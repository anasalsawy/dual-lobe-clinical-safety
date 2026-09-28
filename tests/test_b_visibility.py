from dual_lobe_clinical.prompts import (
    build_execution_prompt,
    build_final_review_prompt,
    build_plan_prompt,
)


def test_a_plan_prompt_is_task_general_and_tool_free():
    prompt = build_plan_prompt(query="send the requested record", patient_context="ctx")
    assert "complete provisional plan" in prompt
    assert "do not execute tools" in prompt.lower()
    assert "diagnosis" in prompt.lower()  # explicitly says not to assume this scenario
    assert "send the requested record" in prompt


def test_b_execution_prompt_has_live_revision_channel():
    prompt = build_execution_prompt(
        query="q",
        patient_context="ctx",
        current_plan_json='{"goal":"g","steps":[]}',
        revision=0,
    )
    assert "consult_planner" in prompt
    assert "never silently" in prompt.lower()
    assert "parallelize" in prompt.lower()


def test_final_review_makes_a_check_b_execution():
    prompt = build_final_review_prompt(
        query="q",
        patient_context="ctx",
        final_plan_json='{"goal":"g"}',
        plan_revision=1,
        execution_report="REPORT",
        delegated_results="CHILD",
        trace_text="TRACE",
    )
    assert "Do not blindly trust B" in prompt
    assert "REPORT" in prompt and "TRACE" in prompt and "CHILD" in prompt
