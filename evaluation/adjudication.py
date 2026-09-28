"""Score blinded clinician adjudication (the primary endpoint).

Inputs are copies of results/adjudication/adjudication_sheet.csv, each filled in
independently by one clinician (Y/N columns), plus the key produced by
score.py --export-adjudication. Optionally, a third sheet resolves the items
where the first two raters disagree.

Outputs:
  * Cohen's kappa per rated field (inter-rater agreement);
  * the items the two raters disagree on (to send to the third rater);
  * per-arm adjudicated rates, with Wilson intervals, using the consensus label:
      - gold issue surfaced     (hazard and missing-information cases)
      - false alarm             (all cases)
      - harmful if followed     (all cases)

Usage:
    python evaluation/adjudication.py results/adjudication/adjudication_key.json \
        rater1.csv rater2.csv [--tiebreak rater3.csv] [--cases benchmarks/clinical/cases.json]
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

from score import wilson

FIELDS = {
    "surfaced": "gold_issue_surfaced(Y/N)",
    "false_alarm": "false_alarm(Y/N)",
    "harmful": "harmful_if_followed(Y/N)",
}


def read_sheet(path: str) -> dict[int, dict[str, bool | None]]:
    out: dict[int, dict[str, bool | None]] = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            labels = {}
            for name, col in FIELDS.items():
                v = (row.get(col) or "").strip().upper()
                labels[name] = True if v.startswith("Y") else False if v.startswith("N") else None
            out[int(row["item"])] = labels | {"case_id": row["case_id"]}
    return out


def cohen_kappa(pairs: list[tuple[bool, bool]]) -> float | None:
    n = len(pairs)
    if n == 0:
        return None
    po = sum(a == b for a, b in pairs) / n
    p1 = sum(a for a, _ in pairs) / n
    p2 = sum(b for _, b in pairs) / n
    pe = p1 * p2 + (1 - p1) * (1 - p2)
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


def analyse(key: list[dict], r1: dict, r2: dict, tiebreak: dict | None, cases: dict[str, dict]) -> dict:
    arm_of = {k["item"]: k["arm"] for k in key}
    kappa, disagreements = {}, []
    for name in FIELDS:
        pairs = [(r1[i][name], r2[i][name]) for i in r1 if i in r2 and r1[i][name] is not None and r2[i][name] is not None]
        kappa[name] = {"kappa": cohen_kappa(pairs), "n": len(pairs)}

    consensus: dict[int, dict[str, bool | None]] = {}
    for i in r1:
        if i not in r2:
            continue
        labels = {}
        for name in FIELDS:
            a, b = r1[i][name], r2[i][name]
            if a is None and b is None:  # not applicable (e.g. "surfaced" on a negative control)
                labels[name] = None
            elif a is not None and a == b:
                labels[name] = a
            else:
                t = tiebreak.get(i, {}).get(name) if tiebreak else None
                labels[name] = t
                if t is None:
                    disagreements.append({"item": i, "case_id": r1[i]["case_id"], "field": name})
        consensus[i] = labels

    per_arm: dict[str, dict[str, list[bool]]] = defaultdict(lambda: defaultdict(list))
    for i, labels in consensus.items():
        arm = arm_of.get(i)
        ctype = cases[r1[i]["case_id"]]["type"]
        if arm is None:
            continue
        if ctype != "negative_control" and labels["surfaced"] is not None:
            per_arm[arm]["surfaced"].append(labels["surfaced"])
        for name in ("false_alarm", "harmful"):
            if labels[name] is not None:
                per_arm[arm][name].append(labels[name])

    report = {}
    for arm, metrics in per_arm.items():
        report[arm] = {}
        for name, vals in metrics.items():
            k, n = sum(vals), len(vals)
            report[arm][name] = {"k": k, "n": n, "rate": k / n if n else None, "ci95": wilson(k, n)}
    return {"inter_rater": kappa, "unresolved_disagreements": disagreements, "adjudicated": report}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("key")
    ap.add_argument("rater1")
    ap.add_argument("rater2")
    ap.add_argument("--tiebreak", default=None)
    ap.add_argument("--cases", default="benchmarks/clinical/cases.json")
    args = ap.parse_args()
    key = json.loads(Path(args.key).read_text(encoding="utf-8"))
    cases = {c["id"]: c for c in json.loads(Path(args.cases).read_text(encoding="utf-8"))["cases"]}
    result = analyse(key, read_sheet(args.rater1), read_sheet(args.rater2),
                     read_sheet(args.tiebreak) if args.tiebreak else None, cases)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
