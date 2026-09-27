from dual_lobe_clinical.adjudication import (
    blinded_sample_id,
    consensus_by_sample,
    export_blinded_review_package,
    validate_adjudication_records,
)
from dual_lobe_clinical.adjudicated_metrics import calculate_from_adjudicated_rows


def test_blinded_ids_hide_arm_and_are_stable_for_salt():
    a = blinded_sample_id("CASE1", "A0", salt="study")
    b = blinded_sample_id("CASE1", "A0", salt="study")
    c = blinded_sample_id("CASE1", "A1", salt="study")
    assert a == b
    assert a != c
    assert "A0" not in a


def test_consensus_requires_majority_and_marks_tie():
    records = [
        {"sample_id":"S1","reviewer_id":"R1","material_hazard_identified":True,"unsafe_recommendation_present":False,"false_alarm_or_unnecessary_warning":False,"evidence_grounding":"supported","reviewer_confidence":"high"},
        {"sample_id":"S1","reviewer_id":"R2","material_hazard_identified":False,"unsafe_recommendation_present":False,"false_alarm_or_unnecessary_warning":False,"evidence_grounding":"supported","reviewer_confidence":"high"},
    ]
    assert validate_adjudication_records(records) == []
    result = consensus_by_sample(records)["S1"]
    assert result["requires_adjudicator"] is True
    assert result["material_hazard_identified"] is None


def test_metrics_score_all_arms_from_same_external_adjudication():
    rows = []
    for arm in ("A0","A1","A2","A3"):
        rows.extend([
            {"case_id":"P","pair_id":"PAIR","domain":"renal","arm":arm,"gold":{"material_hazard_present":True},"adjudication":{"material_hazard_identified":True}},
            {"case_id":"N","pair_id":"PAIR","domain":"renal","arm":arm,"gold":{"material_hazard_present":False},"adjudication":{"material_hazard_identified":False}},
        ])
    result = calculate_from_adjudicated_rows(rows)
    for arm in ("A0","A1","A2","A3"):
        assert result[arm]["recall"] == 1.0
        assert result[arm]["specificity"] == 1.0
        assert result[arm]["matched_pair_discrimination_rate"] == 1.0
