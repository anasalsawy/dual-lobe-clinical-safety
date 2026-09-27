from __future__ import annotations

import argparse
import json
from pathlib import Path

from .adjudication import attach_consensus_to_results, consensus_by_sample
from .adjudicated_metrics import calculate_from_adjudicated_rows
from .statistics import add_confidence_intervals
from .study_runner import sha256_file


def load_jsonl(path: str | Path) -> list[dict]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def score_primary_study(*, run_dir: str | Path, adjudications_path: str | Path) -> dict:
    run_dir=Path(run_dir)
    raw=run_dir/"raw_results.jsonl"
    key_path=run_dir/"PRIVATE_blinding_key.json"
    run_manifest_path=run_dir/"primary_run_manifest.json"

    run_manifest=json.loads(run_manifest_path.read_text(encoding="utf-8"))
    if sha256_file(raw)!=run_manifest["raw_results_sha256"]:
        raise ValueError("raw_results.jsonl changed after blinded review export")

    rows=load_jsonl(raw)
    reviews=load_jsonl(adjudications_path)
    key=json.loads(key_path.read_text(encoding="utf-8"))["mapping"]
    consensus=consensus_by_sample(reviews)
    scored=attach_consensus_to_results(rows,key=key,consensus=consensus)

    if len(scored)!=len(rows):
        raise ValueError(f"primary scoring requires locked consensus for every sample; {len(rows)-len(scored)} unresolved")

    metrics=add_confidence_intervals(calculate_from_adjudicated_rows(scored))
    payload={
        "status":"primary_results_locked",
        "system":"dual_lobe_clinical",
        "metrics":metrics,
        "input_hashes":{
            "raw_results":sha256_file(raw),
            "adjudications":sha256_file(adjudications_path),
            "blinding_key":sha256_file(key_path),
            "primary_run_manifest":sha256_file(run_manifest_path),
        },
    }
    (run_dir/"primary_results.json").write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    return payload


def main() -> None:
    p=argparse.ArgumentParser()
    p.add_argument("--run-dir",required=True)
    p.add_argument("--adjudications",required=True)
    args=p.parse_args()
    print(json.dumps(score_primary_study(run_dir=args.run_dir,adjudications_path=args.adjudications),indent=2))


if __name__=="__main__":
    main()
