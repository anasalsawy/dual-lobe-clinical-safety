from dual_lobe_clinical.models import Plan, PlanContract
from dual_lobe_clinical.tools import ConsultPlannerTool
from dual_lobe_crewai.tools import ProxyToolTrace


def plan(action):
    return Plan(
        goal="g",
        constraints=[],
        steps=[{"id": "S1", "action": action, "parallelizable": True}],
        success_condition="done",
    )


def test_b_can_challenge_and_a_can_revise_live_plan():
    contract = PlanContract(plan("old action"))
    trace = ProxyToolTrace()
    seen = {}

    def a_revision(concern, evidence):
        seen["concern"] = concern
        seen["evidence"] = evidence
        return plan("revised action")

    tool = ConsultPlannerTool(
        contract=contract,
        planner_callback=a_revision,
        trace=trace,
    )
    out = tool._run(
        concern="the old action no longer matches reality",
        evidence="tool returned a different state",
    )

    assert "PLAN_REVISED revision=1" in out
    assert contract.revision == 1
    assert contract.current.steps[0].action == "revised action"
    assert seen == {
        "concern": "the old action no longer matches reality",
        "evidence": "tool returned a different state",
    }
    events = trace.snapshot_from(0)
    assert len(events) == 1
    assert events[0].provenance == "b_to_a_live_channel"


def test_b_challenge_does_not_increment_revision_when_a_upholds_plan():
    original = plan("keep this")
    contract = PlanContract(original)
    trace = ProxyToolTrace()

    tool = ConsultPlannerTool(
        contract=contract,
        planner_callback=lambda concern, evidence: original.model_copy(deep=True),
        trace=trace,
    )
    out = tool._run("is this still valid?", "new observation")

    assert "PLAN_UPHELD revision=0" in out
    assert contract.revision == 0
    assert contract.current.steps[0].action == "keep this"


def test_b_cannot_directly_mutate_contract_through_step_copy():
    contract = PlanContract(plan("immutable"))
    step = contract.step("S1")
    step.action = "silent rewrite"
    assert contract.step("S1").action == "immutable"
