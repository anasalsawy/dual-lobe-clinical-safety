from dual_lobe_clinical.control_gate import GatePolicy, SafetyGate
from dual_lobe_clinical.evidence import FrozenEvidenceStore
from dual_lobe_clinical.schemas import (
    Decision,
    EvidenceRecord,
    FailureType,
    HazardFinding,
    Severity,
    SupervisorAssessment,
)


def evidence_store():
    return FrozenEvidenceStore([
        EvidenceRecord(
            evidence_id="TEST_E1",
            source="synthetic-test-source",
            title="Synthetic benchmark evidence",
            version_or_date="v1",
            excerpt="Synthetic evidence used only to test deterministic gate behavior.",
            tags=("test",),
        )
    ])


def test_pass_when_no_hazard():
    result = SafetyGate(evidence_store()).evaluate(SupervisorAssessment())
    assert result.decision is Decision.PASS


def test_high_severity_grounded_hazard_blocks():
    finding = HazardFinding(
        failure_type=FailureType.MISSED_CONTRAINDICATION,
        severity=Severity.HIGH,
        patient_fact="synthetic patient fact",
        concern="synthetic hazard",
        evidence_ids=("TEST_E1",),
        confidence=0.95,
    )
    result = SafetyGate(evidence_store()).evaluate(
        SupervisorAssessment(findings=(finding,))
    )
    assert result.decision is Decision.BLOCK


def test_missing_evidence_fails_closed():
    finding = HazardFinding(
        failure_type=FailureType.RENAL_HEPATIC_DOSING_RISK,
        severity=Severity.HIGH,
        patient_fact="synthetic patient fact",
        concern="synthetic hazard",
        evidence_ids=("DOES_NOT_EXIST",),
        confidence=0.9,
    )
    result = SafetyGate(evidence_store()).evaluate(
        SupervisorAssessment(findings=(finding,))
    )
    assert result.decision is Decision.INSUFFICIENT_EVIDENCE


def test_evidence_conflict_escalates():
    result = SafetyGate(evidence_store()).evaluate(
        SupervisorAssessment(evidence_conflict=True)
    )
    assert result.decision is Decision.ESCALATE


def test_ungrounded_supervisor_claim_fails_closed():
    result = SafetyGate(evidence_store()).evaluate(
        SupervisorAssessment(supervisor_claims_grounded=False)
    )
    assert result.decision is Decision.INSUFFICIENT_EVIDENCE


def test_moderate_hazard_requires_revision():
    finding = HazardFinding(
        failure_type=FailureType.OMITTED_CONTEXT,
        severity=Severity.MODERATE,
        patient_fact="synthetic patient fact",
        concern="synthetic concern",
        evidence_ids=("TEST_E1",),
        confidence=0.8,
    )
    result = SafetyGate(evidence_store()).evaluate(
        SupervisorAssessment(findings=(finding,))
    )
    assert result.decision is Decision.REVISE
