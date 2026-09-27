from dual_lobe_clinical.control_gate import SafetyGate
from dual_lobe_clinical.evidence import FrozenEvidenceStore
from dual_lobe_clinical.parsing import assessment_from_mapping, merge_assessments
from dual_lobe_clinical.schemas import (
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
            source="test",
            title="Renal test evidence",
            version_or_date="v1",
            excerpt="Synthetic test-only evidence for renal risk.",
            tags=("renal", "kidney"),
        )
    ])


def test_retrieval_is_deterministic_and_traceable():
    s = store()
    first = s.retrieve("kidney renal issue")
    second = s.retrieve("kidney renal issue")
    assert [x.evidence_id for x in first] == ["E1"]
    assert first == second


def test_claim_audit_contradiction_can_block():
    a = assessment_from_mapping({
        "claim_audits": [{
            "claim_id": "C1",
            "claim_text": "synthetic material claim",
            "status": "contradicted",
            "severity_if_wrong": "high",
            "evidence_ids": ["E1"],
            "rationale": "test",
        }]
    })
    result = SafetyGate(store()).evaluate(a)
    assert result.decision is Decision.BLOCK


def test_material_claim_without_evidence_fails_closed():
    a = assessment_from_mapping({
        "claim_audits": [{
            "claim_id": "C1",
            "claim_text": "synthetic material claim",
            "status": "insufficient_evidence",
            "severity_if_wrong": "high",
            "evidence_ids": [],
        }]
    })
    result = SafetyGate(store()).evaluate(a)
    assert result.decision is Decision.INSUFFICIENT_EVIDENCE


def test_merge_preserves_independent_omission_and_final_claim_audit():
    pre = SupervisorAssessment(findings=(
        HazardFinding(
            failure_type=FailureType.OMITTED_CONTEXT,
            severity=Severity.HIGH,
            patient_fact="synthetic fact",
            concern="synthetic omitted hazard",
            evidence_ids=("E1",),
            confidence=0.9,
        ),
    ))
    final = assessment_from_mapping({
        "claim_audits": [{
            "claim_id": "C1",
            "claim_text": "synthetic claim",
            "status": "supported",
            "severity_if_wrong": "moderate",
            "evidence_ids": ["E1"],
        }]
    })
    merged = merge_assessments(pre, final)
    assert len(merged.findings) == 1
    assert len(merged.claim_audits) == 1
    assert merged.claim_audits[0].status is ClaimStatus.SUPPORTED
