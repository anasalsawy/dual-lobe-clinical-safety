import asyncio

from dual_lobe_clinical.models import Plan, PlanContract
from dual_lobe_clinical.tools import (
    CollectExecutionTool,
    ExecutionDelegateState,
    ExecuteParallelTool,
    collect_all_execution_results,
)
from dual_lobe_crewai.tools import ProxyToolTrace


def make_contract():
    return PlanContract(
        Plan(
            goal="g",
            steps=[
                {"id": "S1", "action": "one", "parallelizable": True, "depends_on": []},
                {"id": "S2", "action": "two", "parallelizable": True, "depends_on": []},
                {"id": "S3", "action": "three", "parallelizable": False, "depends_on": []},
                {"id": "S4", "action": "four", "parallelizable": True, "depends_on": ["S1"]},
            ],
            success_condition="done",
        )
    )


def make_tool(contract, state):
    return ExecuteParallelTool(
        contract=contract,
        raw_query="q",
        raw_patient_context="ctx",
        execution_tools=[],
        trace=ProxyToolTrace(),
        run_state=state,
    )


def test_parallel_executor_rejects_non_parallel_step():
    state = ExecutionDelegateState(max_children=2)
    try:
        out = make_tool(make_contract(), state)._run(["S3"])
        assert "not marked parallelizable" in out
        assert state.child_count == 0
    finally:
        state.close()


def test_parallel_executor_rejects_step_with_unsatisfied_dependency():
    state = ExecutionDelegateState(max_children=2)
    try:
        out = make_tool(make_contract(), state)._run(["S4"])
        assert "has dependencies" in out
        assert state.child_count == 0
    finally:
        state.close()


def test_parallel_executor_rejects_unknown_step():
    state = ExecutionDelegateState(max_children=2)
    try:
        try:
            make_tool(make_contract(), state)._run(["NOPE"])
        except KeyError:
            pass
        else:
            raise AssertionError("unknown plan step must be rejected")
    finally:
        state.close()


def test_collect_empty_state_is_nonblocking_and_empty():
    state = ExecutionDelegateState(max_children=2)
    trace = ProxyToolTrace()
    try:
        assert asyncio.run(collect_all_execution_results(state, trace)) == ""
    finally:
        state.close()


def test_collect_tool_reports_no_jobs():
    state = ExecutionDelegateState(max_children=2)
    try:
        tool = CollectExecutionTool(trace=ProxyToolTrace(), run_state=state)
        assert tool._run([], True) == "NO_PARALLEL_EXECUTION_JOBS"
    finally:
        state.close()
