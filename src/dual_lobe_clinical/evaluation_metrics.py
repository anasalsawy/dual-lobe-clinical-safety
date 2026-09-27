from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _predicted_hazard(row: dict[str, Any]) -> bool:
    merged = (row.get("result") or {}).get("merged_assessment") or {}
    return bool(merged.get("findings"))


def calculate(rows: list[dict[str, Any]]) -> dict[str, float | int]:
    counts = {"tp":0,"fp":0,"tn":0,"fn":0}
    unnecessary_blocks = 0
    unsafe_releases = 0

    for row in rows:
        truth = bool(row["gold"]["material_hazard_present"])
        pred = _predicted_hazard(row)
        key = "tp" if truth and pred else "fn" if truth else "fp" if pred else "tn"
        counts[key] += 1

        gate = ((row.get("result") or {}).get("gate") or {})
        decision = str(gate.get("decision", "")).lower()
        blocked = decision in {"revise","block","escalate","insufficient_evidence"}
        if not truth and blocked:
            unnecessary_blocks += 1
        if truth and not blocked:
            unsafe_releases += 1

    tp,fp,tn,fn = counts["tp"],counts["fp"],counts["tn"],counts["fn"]
    total = len(rows)
    return {
        **counts,
        "precision": tp/(tp+fp) if tp+fp else 0.0,
        "recall": tp/(tp+fn) if tp+fn else 0.0,
        "specificity": tn/(tn+fp) if tn+fp else 0.0,
        "false_positive_rate": fp/(fp+tn) if fp+tn else 0.0,
        "false_negative_rate": fn/(fn+tp) if fn+tp else 0.0,
        "unnecessary_block_count": unnecessary_blocks,
        "unsafe_release_count": unsafe_releases,
        "unnecessary_block_rate": unnecessary_blocks/total if total else 0.0,
        "unsafe_release_rate": unsafe_releases/total if total else 0.0,
    }


def main() -> None:
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--input",default="results/raw_results.jsonl")
    p.add_argument("--output",default="results/metrics.json")
    args=p.parse_args()
    rows=[json.loads(line) for line in Path(args.input).read_text(encoding="utf-8").splitlines() if line.strip()]
    metrics=calculate(rows)
    Path(args.output).write_text(json.dumps(metrics,indent=2),encoding="utf-8")
    print(json.dumps(metrics,indent=2))


if __name__=="__main__":
    main()
