import json

import pytest

from dual_lobe_clinical.engine import ClinicalDualLobeEngine
from dual_lobe_clinical.models import ExecutionReport, Plan


def base_plan(action="read local record"):
    return Plan(
        goal="complete the user task",
        constraints=["preserve intent"],
        steps=[
            {"id": "S1", "action": action, "parallelizable": True, "depends_on": []},
            {"id": "S2", "action": "act on result", "parallelizable": False, "depends_on": ["S1"]},
        ],
        success_condition="done",
    )


@pytest.mark.asyncio
async def test_end_to_end_fake_run_preserves_a_b_role_boundary(monkeypatch):
    engine = ClinicalDualLobeEngine()
    seen = {}

    async def fake_plan(*, query, patient_context):
        seen["a_plan_query"] = query
        seen["a_plan_context"] = patient_context
        return base_plan()

    async def fake_execute(
        *,
        raw_query,
        raw_patient_context,
        contract,
        trace,
        planner_callback,
        delegate_state,
    ):
        seen["b_raw_query"] = raw_query
        seen["b_raw_context"] = raw_patient_context
        # Simulate B seeing reality change and using the always-open A channel.
        revised = await engine._revise_plan(
            query=seen["a_plan_query"],
            patient_context=seen["a_plan_context"],
            contract=contract,
            concern="record changed during execution",
            evidence="new local result",
        )
        contract.revise(revised, reason="B challenged plan")
        trace.add(
            "synthetic_execution",
            input_text="raw local work",
            output_text="Jane Doe execution result",
            provenance="test_runtime",
        )
        return json.dumps(
            {
                "plan_revision": contract.revision,
                "steps": [
                    {"id": "S1", "status": "completed", "result": "read"},
                    {"id": "S2", "status": "completed", "result": "acted"},
                ],
                "summary": "done for Jane Doe",
            }
        )

    async def fake_revise(**kwargs):
        seen["revision_concern"] = kwargs["concern"]
        return base_plan(action="read updated local record")

    async def fake_final_review(**kwargs):
        seen["final"] = kwargs
        return "Task completed for <PHI:NAME:FAKE>"

    monkeypatch.setattr(engine, "_make_plan", fake_plan)
    monkeypatch.setattr(engine, "_revise_plan", fake_revise)
    monkeypatch.setattr(engine, "_execute", fake_execute)
    monkeypatch.setattr(engine, "_final_review", fake_final_review)

    delivered = []
    result = await engine.run_clinical(
        query="Update Jane Doe's record",
        patient_context=json.dumps({"name": "Jane Doe", "diagnosis": "asthma"}),
        local_delivery=delivered.append,
    )

    # Remote A side is minimized.
    assert "Jane Doe" not in seen["a_plan_query"]
    assert "Jane Doe" not in seen["a_plan_context"]

    # Local B side receives the original raw task/context.
    assert "Jane Doe" in seen["b_raw_query"]
    assert "Jane Doe" in seen["b_raw_context"]

    # B challenged A and A's revision became the deterministic current contract.
    assert seen["revision_concern"] == "record changed during execution"
    assert result.plan_revision == 1
    assert result.plan.steps[0].action == "read updated local record"

    # B-originated execution material is sanitized before final A review.
    assert "Jane Doe" not in seen["final"]["execution_report"]
    assert "Jane Doe" not in seen["final"]["trace_text"]

    assert result.privacy_receipt.vault_key_destroyed is True
    assert result.trace_event_count >= 2  # plan_frozen + synthetic execution


@pytest.mark.asyncio
async def test_engine_rejects_b_report_from_wrong_plan_revision(monkeypatch):
    engine = ClinicalDualLobeEngine()

    async def fake_plan(**kwargs):
        return base_plan()

    async def fake_execute(**kwargs):
        contract = kwargs["contract"]
        contract.revise(base_plan(action="changed"), reason="changed")
        return json.dumps(
            {
                "plan_revision": 0,
                "steps": [
                    {"id": "S1", "status": "completed"},
                    {"id": "S2", "status": "completed"},
                ],
            }
        )

    monkeypatch.setattr(engine, "_make_plan", fake_plan)
    monkeypatch.setattr(engine, "_execute", fake_execute)

    with pytest.raises(RuntimeError, match="plan revision"):
        await engine.run_clinical(query="q", patient_context="ctx")


@pytest.mark.asyncio
async def test_engine_rejects_b_report_that_drops_required_plan_step(monkeypatch):
    engine = ClinicalDualLobeEngine()

    async def fake_plan(**kwargs):
        return base_plan()

    async def fake_execute(**kwargs):
        return json.dumps(
            {
                "plan_revision": 0,
                "steps": [{"id": "S1", "status": "completed"}],
            }
        )

    monkeypatch.setattr(engine, "_make_plan", fake_plan)
    monkeypatch.setattr(engine, "_execute", fake_execute)

    with pytest.raises(RuntimeError, match="missing plan steps"):
        await engine.run_clinical(query="q", patient_context="ctx")


@pytest.mark.asyncio
async def test_engine_does_not_call_final_a_if_b_report_is_invalid(monkeypatch):
    engine = ClinicalDualLobeEngine()
    called = {"final": False}

    async def fake_plan(**kwargs):
        return base_plan()

    async def fake_execute(**kwargs):
        return json.dumps(
            {
                "plan_revision": 0,
                "steps": [{"id": "BAD", "status": "completed"}],
            }
        )

    async def fake_final(**kwargs):
        called["final"] = True
        return "should not happen"

    monkeypatch.setattr(engine, "_make_plan", fake_plan)
    monkeypatch.setattr(engine, "_execute", fake_execute)
    monkeypatch.setattr(engine, "_final_review", fake_final)

    with pytest.raises(RuntimeError):
        await engine.run_clinical(query="q", patient_context="ctx")
    assert called["final"] is False


@pytest.mark.asyncio
async def test_local_delivery_occurs_only_after_final_a_review(monkeypatch):
    engine = ClinicalDualLobeEngine()
    order = []

    async def fake_plan(**kwargs):
        order.append("plan")
        return base_plan()

    async def fake_execute(**kwargs):
        order.append("execute")
        return json.dumps(
            {
                "plan_revision": 0,
                "steps": [
                    {"id": "S1", "status": "completed"},
                    {"id": "S2", "status": "completed"},
                ],
            }
        )

    async def fake_final(**kwargs):
        order.append("review")
        return "final answer"

    def deliver(text):
        order.append("deliver")

    monkeypatch.setattr(engine, "_make_plan", fake_plan)
    monkeypatch.setattr(engine, "_execute", fake_execute)
    monkeypatch.setattr(engine, "_final_review", fake_final)

    await engine.run_clinical(query="q", patient_context="ctx", local_delivery=deliver)
    assert order == ["plan", "execute", "review", "deliver"]
