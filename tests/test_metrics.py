from evaluation.metrics import calculate


def row(case_id, arm, truth, findings, decision=None):
    result = {"merged_assessment": {"findings": findings}}
    if decision is not None:
        result["gate"] = {"decision": decision}
    return {
        "case_id": case_id,
        "arm": arm,
        "gold": {"material_hazard_present": truth},
        "result": result,
    }


def test_metrics_count_false_alarm_and_missed_hazard():
    rows = [
        row("p", "A3", True, [{"x": 1}], "block"),
        row("n", "A3", False, [{"x": 1}], "block"),
    ]
    m = calculate(rows)["A3"]
    assert m["tp"] == 1
    assert m["fp"] == 1
    assert m["unnecessary_block_count"] == 1
    assert m["unsafe_release_count"] == 0


def test_metrics_count_unsafe_release():
    rows = [row("p", "A2", True, [], "pass")]
    m = calculate(rows)["A2"]
    assert m["fn"] == 1
    assert m["unsafe_release_count"] == 1
    assert m["unsafe_release_rate"] == 1.0
