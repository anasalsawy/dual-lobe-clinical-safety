from __future__ import annotations

from dataclasses import dataclass
from .schemas import ClaimStatus, Decision, GateResult, Severity, SupervisorAssessment


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
    escalate_on_evidence_conflict: bool = True
    fail_closed_on_ungrounded_supervisor_claim: bool = True


class SafetyGate:
    """Deterministic A/B reconciliation gate."""

    def __init__(self, policy: GatePolicy | None = None):
        self.policy = policy or GatePolicy()

    def evaluate(self, assessment: SupervisorAssessment) -> GateResult:
        if self.policy.fail_closed_on_ungrounded_supervisor_claim and not assessment.supervisor_claims_grounded:
            return GateResult(
                Decision.INSUFFICIENT_EVIDENCE,
                ("Supervisor output is ungrounded, malformed, or otherwise not auditable.",),
            )

        if self.policy.escalate_on_evidence_conflict and assessment.evidence_conflict:
            return GateResult(
                Decision.ESCALATE,
                ("Conflicting information requires adjudication.",),
            )

        material_unknown = [
            a for a in assessment.claim_audits
            if a.status is ClaimStatus.INSUFFICIENT_EVIDENCE
            and _SEVERITY_RANK[a.severity_if_wrong] >= _SEVERITY_RANK[Severity.MODERATE]
        ]
        if material_unknown:
            return GateResult(
                Decision.INSUFFICIENT_EVIDENCE,
                ("One or more material clinical claims cannot be resolved from available information.",),
            )

        contradicted = [a for a in assessment.claim_audits if a.status is ClaimStatus.CONTRADICTED]
        if contradicted:
            max_claim_rank = max(_SEVERITY_RANK[a.severity_if_wrong] for a in contradicted)
            if max_claim_rank >= _SEVERITY_RANK[self.policy.block_at]:
                return GateResult(Decision.BLOCK, ("A material clinical claim is contradicted by the supervisory audit.",))
            if max_claim_rank >= _SEVERITY_RANK[self.policy.revise_at]:
                return GateResult(Decision.REVISE, ("A clinical claim requires revision after adversarial audit.",))

        if not assessment.findings:
            if assessment.claim_audits:
                return GateResult(Decision.PASS, ("No material contradiction or unresolved safety issue was found.",))
            return GateResult(Decision.PASS, ("No supervisory hazard detected.",))

        max_rank = max(_SEVERITY_RANK[f.severity] for f in assessment.findings)
        if max_rank >= _SEVERITY_RANK[self.policy.block_at]:
            return GateResult(Decision.BLOCK, ("High-severity or critical context-dependent hazard detected.",))
        if max_rank >= _SEVERITY_RANK[self.policy.revise_at]:
            return GateResult(Decision.REVISE, ("Moderate safety concern requires response revision.",))
        return GateResult(Decision.WARN, ("Low-severity supervisory concern detected.",))
