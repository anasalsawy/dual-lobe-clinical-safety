from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def _predicted_hazard(row: dict[str, Any]) -> bool:
    arm = row["arm"]
    result = row["result"]
    if arm == "A0":
        # A0 has no supervisor; by definition no detected supervisory hazard.
        return False
    if arm == "A1":
        try:
            raw = result.get("self_review_raw", "")
            data = json.loads(raw)
            return bool(data.get("findings"))
        except Exception:
            return False
    merged = result.get("merged_assessment") or {}
    return bool(merged.get("findings"))


def calculate(rows: list[dict[str, Any]]) -> dict[str, dict[str, float | int]]:
    counts = defaultdict(lambda: {"tp": 0, "fp": 0, "tn": 0, "fn": 0})
    for row in rows:
        arm = row["arm"]
        truth = bool(row["gold"]["material_hazard_present"])
        pred = _predicted_hazard(row)
        key = "tp" if truth and pred else "fn" if truth else "fp" if pred else "tn"
        counts[arm][key] += 1

    out: dict[str, dict[str, float | int]] = {}
    for arm, c in counts.items():
        tp, fp, tn, fn = c["tp"], c["fp"], c["tn"], c["fn"]
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        fpr = fp / (fp + tn) if fp + tn else 0.0
        fnr = fn / (fn + tp) if fn + tp else 0.0
        out[arm] = {
            **c,
            "precision": precision,
            "recall": recall,
            "false_positive_rate": fpr,
            "false_negative_rate": fnr,
        }
    return out


def main() -> None:
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--input", default="results/raw_results.jsonl")
    p.add_argument("--output", default="results/metrics.json")
    args = p.parse_args()

    rows = [
        json.loads(line)
        for line in Path(args.input).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    metrics = calculate(rows)
    Path(args.output).write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
