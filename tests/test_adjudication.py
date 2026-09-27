from dual_lobe_clinical.adjudication import (
    blinded_sample_id, consensus_by_sample, export_blinded_review_package, validate_adjudication_records
)
from dual_lobe_clinical.adjudicated_metrics import calculate_from_adjudicated_rows


def test_blinded_ids_are_stable_for_salt():
    a=blinded_sample_id("CASE1",salt="study")
    b=blinded_sample_id("CASE1",salt="study")
    c=blinded_sample_id("CASE2",salt="study")
    assert a==b and a!=c
    assert "CASE1" not in a


def test_consensus_requires_majority_and_marks_tie():
    records=[
        {"sample_id":"S1","reviewer_id":"R1","material_hazard_identified":True,"unsafe_recommendation_present":False,"false_alarm_or_unnecessary_warning":False,"reviewer_confidence":"high"},
        {"sample_id":"S1","reviewer_id":"R2","material_hazard_identified":False,"unsafe_recommendation_present":False,"false_alarm_or_unnecessary_warning":False,"reviewer_confidence":"high"},
    ]
    assert validate_adjudication_records(records)==[]
    result=consensus_by_sample(records)["S1"]
    assert result["requires_adjudicator"] is True
    assert result["material_hazard_identified"] is None


def test_metrics_score_dual_lobe_outputs():
    rows=[
        {"case_id":"P","pair_id":"PAIR","domain":"renal","gold":{"material_hazard_present":True},"adjudication":{"material_hazard_identified":True}},
        {"case_id":"N","pair_id":"PAIR","domain":"renal","gold":{"material_hazard_present":False},"adjudication":{"material_hazard_identified":False}},
    ]
    result=calculate_from_adjudicated_rows(rows)
    assert result["recall"]==1.0
    assert result["specificity"]==1.0
    assert result["matched_pair_discrimination_rate"]==1.0
