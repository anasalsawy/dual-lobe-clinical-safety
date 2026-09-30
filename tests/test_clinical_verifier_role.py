import pytest

import dual_lobe_clinical.engine as engine_module
from dual_lobe_clinical.engine import ClinicalDualLobeEngine


@pytest.mark.asyncio
async def test_no_tools_verifier_uses_dedicated_clinical_verify_role(monkeypatch):
    engine = ClinicalDualLobeEngine()
    verifier_agent = object()
    seen = {}

    monkeypatch.setattr(engine_module, "make_b_verifier", lambda: verifier_agent)

    async def fake_run_one(agent, prompt, expected_output, **kwargs):
        seen.update(agent=agent, prompt=prompt, expected_output=expected_output, **kwargs)
        return "GREEN — the reasoning is supported."

    monkeypatch.setattr(engine_module, "run_one", fake_run_one)

    verdict = await engine._b_verify(
        query="What is the next step?",
        patient_context="No patient data.",
        a_reasoning="The user only needs a direct answer.",
    )

    assert seen["agent"] is verifier_agent
    assert seen["role_key"] == "B_CLINICAL_VERIFY"
    assert seen["state_key"] == "clinical:B_VERIFY"
    assert verdict.deception_level == "GREEN"
