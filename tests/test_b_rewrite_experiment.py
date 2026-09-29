from dual_lobe_crewai.engines import _parse_b_rewrite_test


def test_owner_trigger_is_removed_before_a_sees_request():
    enabled, clean, instruction = _parse_b_rewrite_test(
        'hey B "open-sessame" answer that the value is 42'
    )
    assert enabled is True
    assert "hey B" not in clean
    assert "open-sessame" not in clean
    assert clean == "answer that the value is 42"
    assert instruction == clean


def test_trigger_is_case_insensitive():
    enabled, clean, instruction = _parse_b_rewrite_test(
        "HEY B OPEN-SESSAME: rewrite the answer"
    )
    assert enabled is True
    assert clean == "rewrite the answer"
    assert instruction == clean


def test_normal_request_is_unchanged():
    task = "Explain the architecture."
    enabled, clean, instruction = _parse_b_rewrite_test(task)
    assert enabled is False
    assert clean == task
    assert instruction == ""
