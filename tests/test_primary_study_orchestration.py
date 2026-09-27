import hashlib
import json

import pytest

from dual_lobe_clinical.study_runner import verify_frozen_bundle
from dual_lobe_clinical.primary_score import score_primary_study


def test_verify_frozen_bundle_rejects_changed_file(tmp_path):
    bundle=tmp_path/"bundle"
    bundle.mkdir()
    files={
        "clinical_cases.primary.jsonl":"{}\n",
        "evidence_manifest.primary.json":"{}",
        "guardian_manifest.primary.json":"{}",
        "gold_review_consensus.json":"{}",
    }
    hashes={}
    for name,data in files.items():
        p=bundle/name
        p.write_text(data,encoding="utf-8")
        hashes[name]=hashlib.sha256(p.read_bytes()).hexdigest()
    (bundle/"study_freeze_manifest.json").write_text(json.dumps({
        "status":"primary_frozen","files":hashes
    }),encoding="utf-8")
    verify_frozen_bundle(bundle)
    (bundle/"clinical_cases.primary.jsonl").write_text("changed",encoding="utf-8")
    with pytest.raises(ValueError,match="hash mismatch"):
        verify_frozen_bundle(bundle)


def test_score_primary_refuses_partial_consensus(tmp_path):
    run=tmp_path/"run"
    run.mkdir()
    raw=run/"raw_results.jsonl"
    raw.write_text(json.dumps({
        "case_id":"C1","pair_id":"P1","domain":"x","arm":"A0",
        "gold":{"material_hazard_present":True},"result":{"candidate_answer":"x"}
    })+"\n",encoding="utf-8")
    (run/"PRIVATE_blinding_key.json").write_text(json.dumps({
        "mapping":{"S1":{"case_id":"C1","arm":"A0"}}
    }),encoding="utf-8")
    (run/"primary_run_manifest.json").write_text(json.dumps({
        "raw_results_sha256":hashlib.sha256(raw.read_bytes()).hexdigest()
    }),encoding="utf-8")
    adj=tmp_path/"adj.jsonl"
    adj.write_text("",encoding="utf-8")
    with pytest.raises(ValueError,match="consensus for every sample"):
        score_primary_study(run_dir=run,adjudications_path=adj)
