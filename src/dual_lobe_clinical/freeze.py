from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from .benchmark_validation import assert_valid_cases, load_jsonl
from .evidence import FrozenEvidenceStore
from .evidence_validation import assert_valid_evidence_manifest
from .gold_review import gold_review_consensus
from .guardian import GuardianModelManifest


def sha256_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def build_primary_freeze(
    *,
    cases_path: str | Path,
    evidence_path: str | Path,
    guardian_manifest_path: str | Path,
    gold_reviews_path: str | Path,
    gold_review_key_path: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    cases_path=Path(cases_path)
    evidence_path=Path(evidence_path)
    guardian_manifest_path=Path(guardian_manifest_path)
    gold_reviews_path=Path(gold_reviews_path)
    gold_review_key_path=Path(gold_review_key_path)
    output_dir=Path(output_dir)

    cases=load_jsonl(cases_path)
    evidence=FrozenEvidenceStore.load_json(evidence_path)
    evidence_ids={r.evidence_id for r in evidence.records()}

    assert_valid_cases(
        cases,
        evidence_ids=evidence_ids,
        strict_metadata=True,
    )
    # Provenance must be complete, but development status is allowed here;
    # this command is what creates the immutable primary-frozen bundle.
    assert_valid_evidence_manifest(evidence_path, require_primary_frozen=False)

    guardian=GuardianModelManifest.load(guardian_manifest_path)
    guardian.assert_primary_ready(root=guardian_manifest_path.parent.parent)

    reviews=_load_jsonl(gold_reviews_path)
    consensus=gold_review_consensus(reviews)
    key_payload=json.loads(gold_review_key_path.read_text(encoding="utf-8"))
    mapping=key_payload["mapping"]

    case_to_review={case_id:rid for rid,case_id in mapping.items()}
    missing=[]
    unapproved=[]
    for case in cases:
        cid=case["case_id"]
        rid=case_to_review.get(cid)
        if not rid or rid not in consensus:
            missing.append(cid)
            continue
        if not consensus[rid].get("approved_for_freeze"):
            unapproved.append(cid)

    if missing:
        raise ValueError(f"gold review missing for cases: {missing}")
    if unapproved:
        raise ValueError(f"gold review not approved for cases: {unapproved}")

    output_dir.mkdir(parents=True,exist_ok=False)

    frozen_cases=[]
    for case in cases:
        row=dict(case)
        row["development_only"]=False
        frozen_cases.append(row)
    frozen_cases_path=output_dir/"clinical_cases.primary.jsonl"
    frozen_cases_path.write_text(
        "".join(json.dumps(x,ensure_ascii=False,sort_keys=True)+"\n" for x in frozen_cases),
        encoding="utf-8",
    )

    raw_evidence=json.loads(evidence_path.read_text(encoding="utf-8"))
    raw_evidence["status"]="primary_frozen"
    frozen_evidence_path=output_dir/"evidence_manifest.primary.json"
    frozen_evidence_path.write_text(
        json.dumps(raw_evidence,indent=2,sort_keys=True)+"\n",
        encoding="utf-8",
    )

    frozen_guardian_path=output_dir/"guardian_manifest.primary.json"
    shutil.copy2(guardian_manifest_path,frozen_guardian_path)

    review_consensus_path=output_dir/"gold_review_consensus.json"
    review_consensus_path.write_text(
        json.dumps(consensus,indent=2,sort_keys=True)+"\n",
        encoding="utf-8",
    )

    manifest={
        "freeze_version":"1",
        "status":"primary_frozen",
        "case_count":len(frozen_cases),
        "evidence_record_count":len(evidence.records()),
        "guardian_model_id":guardian.model_id,
        "files":{
            frozen_cases_path.name:sha256_file(frozen_cases_path),
            frozen_evidence_path.name:sha256_file(frozen_evidence_path),
            frozen_guardian_path.name:sha256_file(frozen_guardian_path),
            review_consensus_path.name:sha256_file(review_consensus_path),
        },
        "source_hashes":{
            str(cases_path):sha256_file(cases_path),
            str(evidence_path):sha256_file(evidence_path),
            str(guardian_manifest_path):sha256_file(guardian_manifest_path),
            str(gold_reviews_path):sha256_file(gold_reviews_path),
            str(gold_review_key_path):sha256_file(gold_review_key_path),
        },
    }
    freeze_manifest_path=output_dir/"study_freeze_manifest.json"
    freeze_manifest_path.write_text(
        json.dumps(manifest,indent=2,sort_keys=True)+"\n",
        encoding="utf-8",
    )
    return manifest
