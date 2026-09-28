from dual_lobe_clinical.models import ExecutionReport, Plan, PlanContract


def test_execution_report_cannot_claim_unknown_plan_steps():
    contract = PlanContract(
        Plan(
            goal="g",
            steps=[{"id": "S1", "action": "do x"}],
            success_condition="done",
        )
    )
    report = ExecutionReport.model_validate({
        "plan_revision": 0,
        "steps": [{"id": "S99", "status": "completed", "result": "fake"}],
        "summary": "done",
    })
    try:
        report.assert_matches_contract(contract)
    except RuntimeError as exc:
        assert "outside the current plan" in str(exc)
    else:
        raise AssertionError("unknown B step must be rejected")


def test_execution_report_must_use_current_plan_revision():
    contract = PlanContract(
        Plan(goal="g", steps=[{"id": "S1", "action": "x"}], success_condition="done")
    )
    contract.revise(
        Plan(goal="g", steps=[{"id": "S1", "action": "y"}], success_condition="done"),
        reason="reality changed",
    )
    report = ExecutionReport.model_validate({"plan_revision": 0, "steps": []})
    try:
        report.assert_matches_contract(contract)
    except RuntimeError as exc:
        assert "plan revision" in str(exc)
    else:
        raise AssertionError("stale execution report must be rejected")
