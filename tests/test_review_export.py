import json

from dual_lobe_clinical.adjudication import (
    attach_consensus_to_results,
    export_blinded_review_package,
)


def test_blinded_export_contains_no_case_identity():
    rows = [{
        "case_id":"CASE-1",
        "pair_id":"PAIR",
        "domain":"renal",
        "difficulty":"moderate",
        "patient_context":{"eGFR":19},
        "query":"q",
        "gold":{"material_hazard_present":True},
        "result":{"candidate_answer":"answer"},
    }]
    package, key = export_blinded_review_package(rows, salt="secret")
    serialized = json.dumps(package)
    assert "CASE-1" not in serialized
    sid = package[0]["sample_id"]
    assert key[sid] == "CASE-1"


def test_consensus_attachment_uses_hidden_key():
    rows = [{
        "case_id":"CASE-1",
        "gold":{"material_hazard_present":True},
    }]
    key = {"S-1":"CASE-1"}
    consensus = {
        "S-1":{
            "reviewer_count":2,
            "requires_adjudicator":False,
            "material_hazard_identified":True,
            "unsafe_recommendation_present":False,
            "false_alarm_or_unnecessary_warning":False,
        }
    }
    out = attach_consensus_to_results(rows,key=key,consensus=consensus)
    assert len(out) == 1
    assert out[0]["sample_id"] == "S-1"
    assert out[0]["adjudication"]["material_hazard_identified"] is True
