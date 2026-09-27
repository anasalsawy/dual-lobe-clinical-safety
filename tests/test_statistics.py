from dual_lobe_clinical.statistics import add_confidence_intervals, wilson_interval


def test_wilson_interval_bounds():
    lo,hi=wilson_interval(8,10)
    assert 0<=lo<=0.8<=hi<=1


def test_confidence_intervals_added_to_system_metrics():
    m={"tp":8,"fp":2,"tn":8,"fn":2,"matched_pair_success_count":6,"matched_pair_count":10}
    out=add_confidence_intervals(m)
    assert "recall_ci95" in out
    assert "specificity_ci95" in out
    assert "matched_pair_discrimination_ci95" in out
