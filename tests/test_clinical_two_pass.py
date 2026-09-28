import pytest

from dual_lobe_clinical.models import Plan, PlanContract


def plan(action="first"):
    return Plan(
        goal="complete task",
        constraints=["preserve user intent"],
        steps=[
            {"id": "S1", "action": action, "parallelizable": True, "depends_on": []},
            {"id": "S2", "action": "second", "parallelizable": False, "depends_on": ["S1"]},
        ],
        success_condition="done",
    )


def test_plan_contract_is_frozen_until_a_revision():
    contract = PlanContract(plan())
    before = contract.current_json()
    copy = contract.current
    copy.steps[0].action = "B silently changed it"
    assert contract.current_json() == before
    assert contract.revision == 0


def test_a_revision_replaces_whole_contract_and_increments_revision():
    contract = PlanContract(plan())
    contract.revise(plan("revised by A"), reason="B found new reality")
    assert contract.revision == 1
    assert contract.current.steps[0].action == "revised by A"


def test_plan_rejects_unknown_dependencies():
    with pytest.raises(ValueError):
        Plan(
            goal="g",
            steps=[{"id": "S1", "action": "x", "depends_on": ["MISSING"]}],
            success_condition="done",
        )
