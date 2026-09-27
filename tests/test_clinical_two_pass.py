from dual_lobe_clinical.control_gate import SafetyGate
from dual_lobe_clinical.parsing import assessment_from_mapping, merge_assessments
from dual_lobe_clinical.schemas import ClaimStatus, Decision, FailureType, HazardFinding, Severity, SupervisorAssessment


def test_claim_audit_contradiction_can_block():
    a = assessment_from_mapping({"claim_audits":[{
        "claim_id":"C1","claim_text":"synthetic material claim","status":"contradicted",
        "severity_if_wrong":"high","rationale":"test"
    }]})
    assert SafetyGate().evaluate(a).decision is Decision.BLOCK


def test_material_unresolved_claim_fails_closed():
    a = assessment_from_mapping({"claim_audits":[{
        "claim_id":"C1","claim_text":"synthetic material claim","status":"insufficient_evidence",
        "severity_if_wrong":"high"
    }]})
    assert SafetyGate().evaluate(a).decision is Decision.INSUFFICIENT_EVIDENCE


def test_merge_preserves_independent_omission_and_final_claim_audit():
    pre = SupervisorAssessment(findings=(HazardFinding(
        failure_type=FailureType.OMITTED_CONTEXT,
        severity=Severity.HIGH,
        patient_fact="synthetic fact",
        concern="synthetic omitted hazard",
        confidence=0.9,
    ),))
    final = assessment_from_mapping({"claim_audits":[{
        "claim_id":"C1","claim_text":"synthetic claim","status":"supported","severity_if_wrong":"moderate"
    }]})
    merged = merge_assessments(pre, final)
    assert len(merged.findings) == 1
    assert len(merged.claim_audits) == 1
    assert merged.claim_audits[0].status is ClaimStatus.SUPPORTED
