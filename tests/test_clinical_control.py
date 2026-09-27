from dual_lobe_clinical.control_gate import GatePolicy, SafetyGate
from dual_lobe_clinical.schemas import Decision, FailureType, HazardFinding, Severity, SupervisorAssessment


def test_pass_when_no_hazard():
    assert SafetyGate().evaluate(SupervisorAssessment()).decision is Decision.PASS


def test_high_severity_hazard_blocks():
    finding = HazardFinding(
        failure_type=FailureType.MISSED_CONTRAINDICATION,
        severity=Severity.HIGH,
        patient_fact="synthetic patient fact",
        concern="synthetic hazard",
        confidence=0.95,
    )
    assert SafetyGate().evaluate(SupervisorAssessment(findings=(finding,))).decision is Decision.BLOCK


def test_conflicting_information_escalates():
    assert SafetyGate().evaluate(SupervisorAssessment(evidence_conflict=True)).decision is Decision.ESCALATE


def test_ungrounded_supervisor_claim_fails_closed():
    assert SafetyGate().evaluate(SupervisorAssessment(supervisor_claims_grounded=False)).decision is Decision.INSUFFICIENT_EVIDENCE


def test_moderate_hazard_requires_revision():
    finding = HazardFinding(
        failure_type=FailureType.OMITTED_CONTEXT,
        severity=Severity.MODERATE,
        patient_fact="synthetic patient fact",
        concern="synthetic concern",
        confidence=0.8,
    )
    assert SafetyGate().evaluate(SupervisorAssessment(findings=(finding,))).decision is Decision.REVISE
