from __future__ import annotations

from dataclasses import dataclass

from .evidence import FrozenEvidenceStore
from .schemas import Decision, GateResult, Severity, SupervisorAssessment


_SEVERITY_RANK = {
    Severity.INFO: 0,
    Severity.LOW: 1,
    Severity.MODERATE: 2,
    Severity.HIGH: 3,
    Severity.CRITICAL: 4,
}


@dataclass(frozen=True)
class GatePolicy:
    block_at: Severity = Severity.HIGH
    revise_at: Severity = Severity.MODERATE
    require_evidence_for_moderate_or_higher: bool = True
    escalate_on_evidence_conflict: bool = True
    fail_closed_on_ungrounded_supervisor_claim: bool = True


class SafetyGate:
    """Deterministic A/B reconciliation gate.

    The LLMs may propose findings. This object owns the release decision.
    """

    def __init__(self, evidence: FrozenEvidenceStore, policy: GatePolicy | None = None):
        self.evidence = evidence
        self.policy = policy or GatePolicy()

    def evaluate(self, assessment: SupervisorAssessment) -> GateResult:
        if self.policy.fail_closed_on_ungrounded_supervisor_claim and not assessment.supervisor_claims_grounded:
            return GateResult(
                Decision.INSUFFICIENT_EVIDENCE,
                ("Supervisor produced an ungrounded clinical claim.",),
            )

        if self.policy.escalate_on_evidence_conflict and assessment.evidence_conflict:
            return GateResult(
                Decision.ESCALATE,
                ("Conflicting evidence requires adjudication.",),
            )

        unresolved: list[str] = []
        for finding in assessment.findings:
            needs_evidence = (
                self.policy.require_evidence_for_moderate_or_higher
                and _SEVERITY_RANK[finding.severity] >= _SEVERITY_RANK[Severity.MODERATE]
            )
            if needs_evidence:
                if not finding.evidence_ids:
                    unresolved.append(f"{finding.failure_type.value}:NO_EVIDENCE")
                else:
                    unresolved.extend(
                        eid for eid in finding.evidence_ids if self.evidence.get(eid) is None
                    )

        if unresolved:
            return GateResult(
                Decision.INSUFFICIENT_EVIDENCE,
                ("One or more material supervisory findings lack resolvable evidence.",),
                tuple(sorted(set(unresolved))),
            )

        if not assessment.findings:
            return GateResult(Decision.PASS, ("No supervisory hazard detected.",))

        max_rank = max(_SEVERITY_RANK[f.severity] for f in assessment.findings)
        if max_rank >= _SEVERITY_RANK[self.policy.block_at]:
            return GateResult(
                Decision.BLOCK,
                ("High-severity or critical context-dependent hazard detected.",),
            )
        if max_rank >= _SEVERITY_RANK[self.policy.revise_at]:
            return GateResult(
                Decision.REVISE,
                ("Moderate safety concern requires response revision.",),
            )
        return GateResult(
            Decision.WARN,
            ("Low-severity supervisory concern detected.",),
        )
