import json
import threading

import pytest
from pydantic import ValidationError

from dual_lobe_clinical.models import ExecutionReport, Plan, PlanContract


def make_plan(*, action="fetch current data", second=True):
    steps = [
        {
            "id": "S1",
            "action": action,
            "parallelizable": True,
            "depends_on": [],
        }
    ]
    if second:
        steps.append(
            {
                "id": "S2",
                "action": "use the fetched data",
                "parallelizable": False,
                "depends_on": ["S1"],
            }
        )
    return Plan(
        goal="complete the user's task",
        constraints=["preserve user intent", "do not invent execution"],
        steps=steps,
        success_condition="requested task is actually complete",
    )


def test_plan_rejects_duplicate_step_ids():
    with pytest.raises(ValidationError):
        Plan(
            goal="g",
            steps=[
                {"id": "S1", "action": "x"},
                {"id": "S1", "action": "y"},
            ],
            success_condition="done",
        )


def test_plan_rejects_self_dependency():
    with pytest.raises(ValidationError):
        Plan(
            goal="g",
            steps=[{"id": "S1", "action": "x", "depends_on": ["S1"]}],
            success_condition="done",
        )


def test_plan_rejects_cycles():
    with pytest.raises(ValidationError):
        Plan(
            goal="g",
            steps=[
                {"id": "S1", "action": "x", "depends_on": ["S2"]},
                {"id": "S2", "action": "y", "depends_on": ["S1"]},
            ],
            success_condition="done",
        )


def test_plan_accepts_deep_acyclic_graph():
    plan = Plan(
        goal="g",
        steps=[
            {"id": "S1", "action": "a"},
            {"id": "S2", "action": "b", "depends_on": ["S1"]},
            {"id": "S3", "action": "c", "depends_on": ["S1"]},
            {"id": "S4", "action": "d", "depends_on": ["S2", "S3"]},
        ],
        success_condition="done",
    )
    assert [s.id for s in plan.steps] == ["S1", "S2", "S3", "S4"]


def test_contract_current_is_deep_copy():
    contract = PlanContract(make_plan())
    leaked = contract.current
    leaked.constraints.append("B-added")
    leaked.steps[0].action = "B-rewrite"
    again = contract.current
    assert "B-added" not in again.constraints
    assert again.steps[0].action == "fetch current data"


def test_contract_fingerprint_is_stable_without_revision():
    contract = PlanContract(make_plan())
    assert contract.fingerprint() == contract.fingerprint()


def test_contract_fingerprint_changes_only_when_plan_changes():
    contract = PlanContract(make_plan())
    before = contract.fingerprint()
    contract.revise(make_plan(action="fetch revised data"), reason="reality changed")
    assert contract.revision == 1
    assert contract.fingerprint() != before


def test_contract_revision_is_thread_safe():
    contract = PlanContract(make_plan())
    errors = []

    def revise(i):
        try:
            contract.revise(make_plan(action=f"revision-{i}"), reason=f"r{i}")
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=revise, args=(i,)) for i in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors
    assert contract.revision == 20
    assert contract.current.steps[0].action.startswith("revision-")


def test_plan_parser_accepts_fenced_json():
    raw = """```json
    {"goal":"g","constraints":[],"steps":[{"id":"S1","action":"x"}],"success_condition":"done"}
    ```"""
    assert Plan.from_text(raw).steps[0].id == "S1"


def test_plan_parser_rejects_non_object_json():
    with pytest.raises(ValueError):
        Plan.from_text('["not", "a", "plan"]')


def test_execution_report_rejects_unknown_step():
    contract = PlanContract(make_plan(second=False))
    report = ExecutionReport.model_validate(
        {
            "plan_revision": 0,
            "steps": [
                {"id": "S99", "status": "completed", "result": "invented"}
            ],
        }
    )
    with pytest.raises(RuntimeError, match="outside the current plan"):
        report.assert_matches_contract(contract)


def test_execution_report_rejects_stale_revision():
    contract = PlanContract(make_plan(second=False))
    contract.revise(make_plan(action="new", second=False), reason="changed")
    report = ExecutionReport.model_validate(
        {"plan_revision": 0, "steps": [{"id": "S1", "status": "completed"}]}
    )
    with pytest.raises(RuntimeError, match="plan revision"):
        report.assert_matches_contract(contract)


def test_execution_report_rejects_duplicate_step_reports():
    contract = PlanContract(make_plan(second=False))
    report = ExecutionReport.model_validate(
        {
            "plan_revision": 0,
            "steps": [
                {"id": "S1", "status": "completed"},
                {"id": "S1", "status": "failed"},
            ],
        }
    )
    with pytest.raises(RuntimeError, match="duplicate"):
        report.assert_matches_contract(contract)


def test_execution_report_requires_every_current_plan_step():
    contract = PlanContract(make_plan(second=True))
    report = ExecutionReport.model_validate(
        {
            "plan_revision": 0,
            "steps": [{"id": "S1", "status": "completed"}],
        }
    )
    with pytest.raises(RuntimeError, match="missing plan steps"):
        report.assert_matches_contract(contract)


def test_execution_report_accepts_completed_failed_or_not_run_for_all_steps():
    contract = PlanContract(make_plan(second=True))
    report = ExecutionReport.model_validate(
        {
            "plan_revision": 0,
            "steps": [
                {"id": "S1", "status": "completed", "evidence": "receipt"},
                {"id": "S2", "status": "not_run", "result": "dependency failed"},
            ],
        }
    )
    report.assert_matches_contract(contract)
