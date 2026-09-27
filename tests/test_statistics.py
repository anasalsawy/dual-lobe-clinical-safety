from dual_lobe_clinical.statistics import (
    exact_mcnemar_pvalue,
    paired_arm_comparison,
    wilson_interval,
)


def test_wilson_interval_bounds():
    lo, hi = wilson_interval(8, 10)
    assert 0 <= lo <= 0.8 <= hi <= 1


def test_exact_mcnemar_no_disagreement_is_one():
    assert exact_mcnemar_pvalue(0, 0) == 1.0


def test_exact_mcnemar_detects_strong_one_sided_discordance():
    assert exact_mcnemar_pvalue(10, 0) < 0.01


def test_paired_arm_comparison_uses_same_case_ids():
    rows = [
        {"case_id":"1","arm":"A0","adjudication":{"material_hazard_identified":False}},
        {"case_id":"1","arm":"A2","adjudication":{"material_hazard_identified":True}},
        {"case_id":"2","arm":"A0","adjudication":{"material_hazard_identified":False}},
        {"case_id":"2","arm":"A2","adjudication":{"material_hazard_identified":False}},
    ]
    result = paired_arm_comparison(rows, arm_a="A0", arm_b="A2")
    assert result["paired_case_count"] == 2
    assert result["arm_b_positive_arm_a_negative"] == 1
