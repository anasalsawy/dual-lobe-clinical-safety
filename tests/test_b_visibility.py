from dual_lobe_clinical.prompts import (
    build_final_audit_prompt,
    build_independent_prompt,
)


def test_independent_b_prompt_has_no_a_answer_channel():
    marker = "SECRET_A_ANSWER_MUST_NOT_APPEAR"
    prompt = build_independent_prompt(
        query="synthetic query",
        patient_context="synthetic context",
        evidence_text="E1 synthetic evidence",
    )
    assert marker not in prompt
    assert "NOT being shown A's answer" in prompt
    assert "synthetic query" in prompt
    assert "synthetic context" in prompt


def test_final_b_prompt_contains_exact_a_answer_and_full_observable_trace():
    answer = "EXACT_A_CANDIDATE_123"
    trace = (
        "[1] tool=retrieve\nprovenance=test\ninput=x\noutput=RESULT_ONE\n\n"
        "[2] tool=delegate_child\nprovenance=test\ninput=y\noutput=RESULT_TWO"
    )
    prompt = build_final_audit_prompt(
        query="q",
        patient_context="ctx",
        independent_json='{"findings":[]}',
        a_answer=answer,
        delegated_results="CHILD_RESULT",
        trace_text=trace,
        evidence_text="E1",
    )
    assert answer in prompt
    assert trace in prompt
    assert "CHILD_RESULT" in prompt
    assert "COMPLETE OBSERVABLE A/CHILD EXECUTION + PROVENANCE TRACE" in prompt


def test_final_audit_explicitly_requires_every_material_claim():
    prompt = build_final_audit_prompt(
        query="q",
        patient_context="ctx",
        independent_json='{"findings":[]}',
        a_answer="candidate",
        delegated_results="",
        trace_text="trace",
        evidence_text="evidence",
    )
    assert "Every material A clinical claim must appear in claim_audits" in prompt
    assert "Do not treat agreement between A and B as evidence" in prompt
