import json

import pytest

from dual_lobe_clinical.engine import ClinicalDualLobeEngine
from dual_lobe_clinical.evidence import FrozenEvidenceStore
from dual_lobe_clinical.privacy import PrivacyGuard, ProviderPrivacyPolicy


@pytest.mark.asyncio
async def test_runtime_sends_only_tokenized_identity_to_both_passes(monkeypatch):
    engine = ClinicalDualLobeEngine(
        evidence_store=FrozenEvidenceStore(),
        privacy_guard=PrivacyGuard(
            ProviderPrivacyPolicy(provider_name="test"),
            audit_key=b"test-key",
        ),
    )
    seen = {"a_task": "", "b_independent": ("", ""), "final": ("", "", "")}

    async def fake_run_a(**kwargs):
        seen["a_task"] = kwargs["task"]
        return "Advice for <PHI:NAME:DEADBEEF1234>"

    async def fake_independent(**kwargs):
        seen["b_independent"] = (kwargs["query"], kwargs["patient_context"])
        from dual_lobe_clinical.schemas import SupervisorAssessment
        return SupervisorAssessment()

    async def fake_final(**kwargs):
        seen["final"] = (
            kwargs["query"],
            kwargs["patient_context"],
            kwargs["trace_text"],
        )
        from dual_lobe_clinical.schemas import SupervisorAssessment
        return SupervisorAssessment()

    monkeypatch.setattr(engine, "_run_a", fake_run_a)
    monkeypatch.setattr(engine, "_independent_pass", fake_independent)
    monkeypatch.setattr(engine, "_final_clinical_audit", fake_final)

    result = await engine.run_clinical(
        query="What should Jane Doe do?",
        patient_context=json.dumps({"name": "Jane Doe", "diagnosis": "asthma"}),
    )

    combined = json.dumps(seen)
    assert "Jane Doe" not in combined
    assert "Jane Doe" not in json.dumps({
        "q": result.sanitized_query,
        "ctx": result.sanitized_patient_context,
    })
    assert result.privacy_receipt.vault_key_destroyed is True
    assert result.privacy_receipt.persisted_raw_locally is False


@pytest.mark.asyncio
async def test_local_delivery_can_rehydrate_without_persisting_raw_in_result(monkeypatch):
    engine = ClinicalDualLobeEngine(
        evidence_store=FrozenEvidenceStore(),
        privacy_guard=PrivacyGuard(audit_key=b"test-key"),
    )
    captured = []

    async def fake_run_a(**kwargs):
        task = kwargs["task"]
        start = task.index("<PHI:NAME:")
        end = task.index(">", start) + 1
        token = task[start:end]
        return f"Follow-up for {token}"

    async def empty(**kwargs):
        from dual_lobe_clinical.schemas import SupervisorAssessment
        return SupervisorAssessment()

    monkeypatch.setattr(engine, "_run_a", fake_run_a)
    monkeypatch.setattr(engine, "_independent_pass", empty)
    monkeypatch.setattr(engine, "_final_clinical_audit", empty)

    result = await engine.run_clinical(
        query="Plan follow-up",
        patient_context=json.dumps({"name": "Jane Doe", "diagnosis": "asthma"}),
        local_delivery=captured.append,
    )

    assert captured == ["Follow-up for Jane Doe"]
    assert "Jane Doe" not in (result.released_answer or "")
    assert "Jane Doe" not in result.sanitized_patient_context
    assert result.privacy_receipt.vault_key_destroyed is True
