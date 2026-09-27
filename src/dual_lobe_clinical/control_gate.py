from __future__ import annotations

from dataclasses import dataclass

from .evidence import FrozenEvidenceStore
from .schemas import (
    ClaimStatus,
    Decision,
    GateResult,
    Severity,
    SupervisorAssessment,
)


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

    Models propose findings and claim audits. Deterministic code owns the
    release decision so neither A nor B can wave through its own output.
    """

    def __init__(self, evidence: FrozenEvidenceStore, policy: GatePolicy | None = None):
        self.evidence = evidence
        self.policy = policy or GatePolicy()

    def evaluate(self, assessment: SupervisorAssessment) -> GateResult:
        if self.policy.fail_closed_on_ungrounded_supervisor_claim and not assessment.supervisor_claims_grounded:
            return GateResult(
                Decision.INSUFFICIENT_EVIDENCE,
                ("Supervisor produced an ungrounded or unparseable clinical assessment.",),
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

        for audit in assessment.claim_audits:
            material = _SEVERITY_RANK[audit.severity_if_wrong] >= _SEVERITY_RANK[Severity.MODERATE]
            if audit.status is ClaimStatus.INSUFFICIENT_EVIDENCE and material:
                unresolved.append(f"{audit.claim_id}:INSUFFICIENT_EVIDENCE")
            if material and audit.evidence_ids:
                unresolved.extend(
                    eid for eid in audit.evidence_ids if self.evidence.get(eid) is None
                )

        if unresolved:
            return GateResult(
                Decision.INSUFFICIENT_EVIDENCE,
                ("One or more material findings or A claims lack resolvable evidence.",),
                tuple(sorted(set(unresolved))),
            )

        contradicted = [
            a for a in assessment.claim_audits
            if a.status is ClaimStatus.CONTRADICTED
        ]
        if contradicted:
            max_claim_rank = max(_SEVERITY_RANK[a.severity_if_wrong] for a in contradicted)
            if max_claim_rank >= _SEVERITY_RANK[self.policy.block_at]:
                return GateResult(
                    Decision.BLOCK,
                    ("A material clinical claim is contradicted by the supervisory audit.",),
                )
            if max_claim_rank >= _SEVERITY_RANK[self.policy.revise_at]:
                return GateResult(
                    Decision.REVISE,
                    ("A clinical claim requires revision after adversarial audit.",),
                )

        if not assessment.findings:
            if assessment.claim_audits:
                return GateResult(Decision.PASS, ("All material audited claims are supported.",))
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
