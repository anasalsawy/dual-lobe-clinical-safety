from __future__ import annotations

import argparse
import json
from pathlib import Path

from dual_lobe_clinical.adjudication import (
    attach_consensus_to_results,
    consensus_by_sample,
)
from dual_lobe_clinical.adjudicated_metrics import calculate_from_adjudicated_rows


def load_jsonl(path: str) -> list[dict]:
    return [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--results", default="results/raw_results.jsonl")
    p.add_argument("--adjudications", default="results/review/adjudications.jsonl")
    p.add_argument("--blinding-key", default="results/review/blinding_key.json")
    p.add_argument("--output", default="results/adjudicated_metrics.json")
    args = p.parse_args()

    result_rows = load_jsonl(args.results)
    reviews = load_jsonl(args.adjudications)
    key_payload = json.loads(Path(args.blinding_key).read_text(encoding="utf-8"))
    key = key_payload["mapping"]

    consensus = consensus_by_sample(reviews)
    scored_rows = attach_consensus_to_results(
        result_rows,
        key=key,
        consensus=consensus,
    )
    if not scored_rows:
        raise SystemExit("No locked consensus rows available for scoring.")

    metrics = calculate_from_adjudicated_rows(scored_rows)
    Path(args.output).write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
