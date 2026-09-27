import hashlib
import json
from pathlib import Path

import pytest

from dual_lobe_clinical.freeze import build_primary_freeze


def write_jsonl(path, rows):
    path.write_text("".join(json.dumps(x)+"\n" for x in rows),encoding="utf-8")


def test_freeze_refuses_missing_gold_review(tmp_path):
    cases=tmp_path/"cases.jsonl"
    evidence=tmp_path/"evidence.json"
    guardian_dir=tmp_path/"guardian"
    guardian_dir.mkdir()
    artifact=tmp_path/"guardian.bin"
    artifact.write_bytes(b"guardian")
    guardian=guardian_dir/"manifest.json"
    reviews=tmp_path/"reviews.jsonl"
    key=tmp_path/"key.json"

    write_jsonl(cases,[{
        "case_id":"C1","pair_id":"P","domain":"x","difficulty":"moderate",
        "patient_context":{},"query":"q",
        "gold":{
            "material_hazard_present":True,
            "failure_types":["F01"],"expected_gate":"block",
            "evidence_ids":["E1"],"required_safety_concepts":["x"]
        }
    },{
        "case_id":"C2","pair_id":"P","domain":"x","difficulty":"moderate",
        "patient_context":{},"query":"q",
        "gold":{
            "material_hazard_present":False,
            "failure_types":[],"expected_gate":"pass",
            "evidence_ids":[],"required_safety_concepts":[]
        }
    }])
    evidence.write_text(json.dumps({
        "corpus_version":"1","status":"development_validated","records":[{
            "evidence_id":"E1","source":"s","title":"t","version_or_date":"v",
            "excerpt":"x","tags":["x"],"source_url":"https://example.org/x",
            "source_org":"org","source_type":"peer_reviewed_study",
            "effective_date":"2026-01-01","accessed_at":"2026-01-02",
            "source_locator":"section"
        }]
    }),encoding="utf-8")
    guardian.write_text(json.dumps({
        "manifest_version":"1","model_id":"g","base_model":"b",
        "fine_tune_profile":"f","artifact_path":str(artifact),
        "artifact_sha256":hashlib.sha256(artifact.read_bytes()).hexdigest(),
        "training_data_version":"t",
        "intended_roles":[
            "clinical_context_broadening","adversarial_claim_audit",
            "privacy_oversight","evidence_discipline"
        ]
    }),encoding="utf-8")
    reviews.write_text("",encoding="utf-8")
    key.write_text(json.dumps({"mapping":{}}),encoding="utf-8")

    with pytest.raises(ValueError,match="gold review missing"):
        build_primary_freeze(
            cases_path=cases,evidence_path=evidence,
            guardian_manifest_path=guardian,gold_reviews_path=reviews,
            gold_review_key_path=key,output_dir=tmp_path/"frozen",
        )
