from dual_lobe_clinical.gold_review import (
    export_gold_review_cases,
    gold_review_consensus,
    validate_gold_reviews,
)


def sample_case():
    return {
        "case_id":"C1",
        "patient_context":{"x":1},
        "query":"q",
        "gold":{
            "material_hazard_present":True,
            "failure_types":["F01"],
            "expected_gate":"block",
            "evidence_ids":["E1"],
            "required_safety_concepts":["concept"],
        },
    }


def test_gold_review_export_separates_internal_case_id():
    packet,key=export_gold_review_cases([sample_case()],salt="s")
    assert packet[0]["review_id"] != "C1"
    assert key[packet[0]["review_id"]] == "C1"


def test_two_agreeing_reviewers_approve_case():
    common={
        "review_id":"G1",
        "hazard_label_correct":True,
        "negative_control_is_truly_negative":True,
        "expected_gate_appropriate":True,
        "evidence_supports_gold":True,
        "wording_is_clinically_plausible":True,
        "reviewer_confidence":"high",
    }
    rows=[{**common,"reviewer_id":"R1"},{**common,"reviewer_id":"R2"}]
    assert validate_gold_reviews(rows)==[]
    consensus=gold_review_consensus(rows)["G1"]
    assert consensus["approved_for_freeze"] is True


def test_disagreement_requires_adjudication():
    a={
        "review_id":"G1","reviewer_id":"R1",
        "hazard_label_correct":True,
        "negative_control_is_truly_negative":True,
        "expected_gate_appropriate":True,
        "evidence_supports_gold":True,
        "wording_is_clinically_plausible":True,
        "reviewer_confidence":"high",
    }
    b={**a,"reviewer_id":"R2","hazard_label_correct":False}
    consensus=gold_review_consensus([a,b])["G1"]
    assert consensus["requires_adjudication"] is True
    assert consensus["approved_for_freeze"] is False
