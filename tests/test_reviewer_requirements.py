import json

import pytest

from dual_lobe_clinical.control_gate import GatePolicy, SafetyGate
from dual_lobe_clinical.evidence import FrozenEvidenceStore
from dual_lobe_clinical.parsing import assessment_from_json, assessment_from_mapping, merge_assessments
from dual_lobe_clinical.schemas import (
    ClaimAudit,
    ClaimStatus,
    Decision,
    EvidenceRecord,
    FailureType,
    HazardFinding,
    Severity,
    SupervisorAssessment,
)


def store():
    return FrozenEvidenceStore([
        EvidenceRecord(
            evidence_id="E1",
            source="synthetic",
            title="Synthetic evidence one",
            version_or_date="v1",
            excerpt="Test-only support for a material safety concern.",
            tags=("test", "safety"),
        ),
        EvidenceRecord(
            evidence_id="E2",
            source="synthetic",
            title="Synthetic evidence two",
            version_or_date="v1",
            excerpt="Second test-only record.",
            tags=("test", "conflict"),
        ),
    ])


def test_a_correct_b_wrong_fails_closed_when_b_ungrounded():
    assessment = SupervisorAssessment(
        supervisor_claims_grounded=False,
        notes=("B asserted a hazard without support",),
    )
    assert SafetyGate(store()).evaluate(assessment).decision is Decision.INSUFFICIENT_EVIDENCE


def test_a_wrong_b_correct_high_risk_blocks():
    assessment = assessment_from_mapping({
        "claim_audits": [{
            "claim_id": "C1",
            "claim_text": "material synthetic claim",
            "status": "contradicted",
            "severity_if_wrong": "high",
            "evidence_ids": ["E1"],
            "rationale": "contradicted by frozen evidence",
        }]
    })
    assert SafetyGate(store()).evaluate(assessment).decision is Decision.BLOCK


def test_both_wrong_cannot_pass_when_material_claim_unverified():
    assessment = assessment_from_mapping({
        "claim_audits": [{
            "claim_id": "C1",
            "claim_text": "unsupported agreement",
            "status": "insufficient_evidence",
            "severity_if_wrong": "high",
            "evidence_ids": [],
        }]
    })
    assert SafetyGate(store()).evaluate(assessment).decision is Decision.INSUFFICIENT_EVIDENCE


def test_conflicting_evidence_escalates():
    assessment = SupervisorAssessment(evidence_conflict=True)
    assert SafetyGate(store()).evaluate(assessment).decision is Decision.ESCALATE


def test_malformed_b_output_fails_closed():
    assessment = assessment_from_json("not-json")
    assert assessment.supervisor_claims_grounded is False
    assert SafetyGate(store()).evaluate(assessment).decision is Decision.INSUFFICIENT_EVIDENCE


def test_unknown_evidence_id_fails_closed():
    assessment = SupervisorAssessment(findings=(
        HazardFinding(
            failure_type=FailureType.MISSED_CONTRAINDICATION,
            severity=Severity.HIGH,
            patient_fact="synthetic fact",
            concern="synthetic concern",
            evidence_ids=("MISSING",),
            confidence=0.9,
        ),
    ))
    result = SafetyGate(store()).evaluate(assessment)
    assert result.decision is Decision.INSUFFICIENT_EVIDENCE
    assert "MISSING" in result.unresolved_evidence_ids


def test_low_risk_warning_is_not_promoted_to_block():
    assessment = SupervisorAssessment(findings=(
        HazardFinding(
            failure_type=FailureType.OMITTED_CONTEXT,
            severity=Severity.LOW,
            patient_fact="synthetic fact",
            concern="minor concern",
            confidence=0.6,
        ),
    ))
    assert SafetyGate(store()).evaluate(assessment).decision is Decision.WARN


def test_negative_control_no_findings_passes():
    assert SafetyGate(store()).evaluate(SupervisorAssessment()).decision is Decision.PASS


def test_independent_finding_survives_final_audit_merge():
    pre = SupervisorAssessment(findings=(
        HazardFinding(
            failure_type=FailureType.MISSED_CONTRAINDICATION,
            severity=Severity.HIGH,
            patient_fact="synthetic fact",
            concern="latent hazard",
            evidence_ids=("E1",),
            confidence=0.9,
        ),
    ))
    final = SupervisorAssessment(claim_audits=(
        ClaimAudit(
            claim_id="C1",
            claim_text="A claim",
            status=ClaimStatus.SUPPORTED,
            severity_if_wrong=Severity.MODERATE,
            evidence_ids=("E1",),
        ),
    ))
    merged = merge_assessments(pre, final)
    assert merged.findings == pre.findings
    assert merged.claim_audits == final.claim_audits
    assert SafetyGate(store()).evaluate(merged).decision is Decision.BLOCK


def test_retrieval_same_query_same_order():
    s = store()
    a = [x.evidence_id for x in s.retrieve("synthetic safety test")]
    b = [x.evidence_id for x in s.retrieve("synthetic safety test")]
    assert a == b


def test_gate_policy_boundary_is_deterministic():
    policy = GatePolicy(block_at=Severity.CRITICAL, revise_at=Severity.HIGH)
    assessment = SupervisorAssessment(findings=(
        HazardFinding(
            failure_type=FailureType.OMITTED_CONTEXT,
            severity=Severity.HIGH,
            patient_fact="synthetic",
            concern="synthetic",
            evidence_ids=("E1",),
            confidence=1.0,
        ),
    ))
    assert SafetyGate(store(), policy).evaluate(assessment).decision is Decision.REVISE
