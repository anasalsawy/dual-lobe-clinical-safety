from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from .benchmark_runner import main_async as benchmark_main_async
from .export_review import load_jsonl as load_results
from .adjudication import export_blinded_review_package, write_jsonl


def sha256_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_frozen_bundle(bundle: str | Path) -> dict:
    bundle=Path(bundle)
    manifest_path=bundle/"study_freeze_manifest.json"
    manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status")!="primary_frozen":
        raise ValueError("study bundle is not primary_frozen")
    for name, expected in (manifest.get("files") or {}).items():
        path=bundle/name
        if not path.exists():
            raise ValueError(f"frozen study file missing: {name}")
        if sha256_file(path)!=expected:
            raise ValueError(f"frozen study hash mismatch: {name}")
    required={"clinical_cases.primary.jsonl","guardian_manifest.primary.json","gold_review_consensus.json"}
    missing=[x for x in required if not (bundle/x).exists()]
    if missing:
        raise ValueError(f"frozen study bundle missing required files: {missing}")
    return manifest


async def run_primary_bundle(*, bundle: str | Path, output_dir: str | Path, blinding_salt: str) -> dict:
    bundle=Path(bundle)
    output_dir=Path(output_dir)
    output_dir.mkdir(parents=True,exist_ok=False)
    freeze_manifest=verify_frozen_bundle(bundle)

    raw=output_dir/"raw_results.jsonl"
    args=SimpleNamespace(
        cases=str(bundle/"clinical_cases.primary.jsonl"),
        output=str(raw),
        study_mode="primary",
        guardian_manifest=str(bundle/"guardian_manifest.primary.json"),
    )
    await benchmark_main_async(args)

    rows=load_results(str(raw))
    review,key=export_blinded_review_package(rows,salt=blinding_salt)
    review_dir=output_dir/"blinded_review"
    review_dir.mkdir()
    review_path=review_dir/"review_packet.jsonl"
    key_path=output_dir/"PRIVATE_blinding_key.json"
    write_jsonl(review_path,review)
    key_path.write_text(json.dumps({
        "mapping":key,
        "blinding_salt":blinding_salt,
        "warning":"Do not provide this file to blinded reviewers."
    },indent=2),encoding="utf-8")

    run_manifest={
        "status":"awaiting_blinded_adjudication",
        "system":"dual_lobe_clinical",
        "freeze_manifest_sha256":sha256_file(bundle/"study_freeze_manifest.json"),
        "raw_results_sha256":sha256_file(raw),
        "review_packet_sha256":sha256_file(review_path),
        "case_count":freeze_manifest.get("case_count"),
        "sample_count":len(review),
        "next_step":"Collect >=2 blinded clinician adjudications per sample, then score the study.",
    }
    (output_dir/"primary_run_manifest.json").write_text(json.dumps(run_manifest,indent=2)+"\n",encoding="utf-8")
    return run_manifest


def main() -> None:
    p=argparse.ArgumentParser(description="Run the frozen Dual-Lobe clinical benchmark and export blinded review samples.")
    p.add_argument("--bundle",required=True)
    p.add_argument("--output-dir",required=True)
    p.add_argument("--blinding-salt",required=True)
    args=p.parse_args()
    print(json.dumps(asyncio.run(run_primary_bundle(
        bundle=args.bundle, output_dir=args.output_dir, blinding_salt=args.blinding_salt
    )),indent=2))


if __name__=="__main__":
    main()
