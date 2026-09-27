from dual_lobe_clinical.control_gate import GatePolicy, SafetyGate
from dual_lobe_clinical.parsing import assessment_from_json, assessment_from_mapping, merge_assessments
from dual_lobe_clinical.schemas import ClaimAudit, ClaimStatus, Decision, FailureType, HazardFinding, Severity, SupervisorAssessment


def test_a_correct_b_wrong_fails_closed_when_b_ungrounded():
    a = SupervisorAssessment(supervisor_claims_grounded=False)
    assert SafetyGate().evaluate(a).decision is Decision.INSUFFICIENT_EVIDENCE


def test_a_wrong_b_correct_high_risk_blocks():
    a = assessment_from_mapping({"claim_audits":[{
        "claim_id":"C1","claim_text":"material synthetic claim","status":"contradicted",
        "severity_if_wrong":"high","rationale":"contradicted by supervisory audit"
    }]})
    assert SafetyGate().evaluate(a).decision is Decision.BLOCK


def test_both_wrong_cannot_pass_when_material_claim_unresolved():
    a = assessment_from_mapping({"claim_audits":[{
        "claim_id":"C1","claim_text":"unsupported agreement","status":"insufficient_evidence",
        "severity_if_wrong":"high"
    }]})
    assert SafetyGate().evaluate(a).decision is Decision.INSUFFICIENT_EVIDENCE


def test_conflicting_information_escalates():
    assert SafetyGate().evaluate(SupervisorAssessment(evidence_conflict=True)).decision is Decision.ESCALATE


def test_malformed_b_output_fails_closed():
    a = assessment_from_json("not-json")
    assert a.supervisor_claims_grounded is False
    assert SafetyGate().evaluate(a).decision is Decision.INSUFFICIENT_EVIDENCE


def test_low_risk_warning_is_not_promoted_to_block():
    a = SupervisorAssessment(findings=(HazardFinding(
        failure_type=FailureType.OMITTED_CONTEXT,severity=Severity.LOW,
        patient_fact="synthetic fact",concern="minor concern",confidence=0.6
    ),))
    assert SafetyGate().evaluate(a).decision is Decision.WARN


def test_negative_control_no_findings_passes():
    assert SafetyGate().evaluate(SupervisorAssessment()).decision is Decision.PASS


def test_independent_finding_survives_final_audit_merge():
    pre = SupervisorAssessment(findings=(HazardFinding(
        failure_type=FailureType.MISSED_CONTRAINDICATION,severity=Severity.HIGH,
        patient_fact="synthetic fact",concern="latent hazard",confidence=0.9
    ),))
    final = SupervisorAssessment(claim_audits=(ClaimAudit(
        claim_id="C1",claim_text="A claim",status=ClaimStatus.SUPPORTED,severity_if_wrong=Severity.MODERATE
    ),))
    merged = merge_assessments(pre, final)
    assert merged.findings == pre.findings
    assert merged.claim_audits == final.claim_audits
    assert SafetyGate().evaluate(merged).decision is Decision.BLOCK


def test_gate_policy_boundary_is_deterministic():
    policy = GatePolicy(block_at=Severity.CRITICAL, revise_at=Severity.HIGH)
    a = SupervisorAssessment(findings=(HazardFinding(
        failure_type=FailureType.OMITTED_CONTEXT,severity=Severity.HIGH,
        patient_fact="synthetic",concern="synthetic",confidence=1.0
    ),))
    assert SafetyGate(policy).evaluate(a).decision is Decision.REVISE
