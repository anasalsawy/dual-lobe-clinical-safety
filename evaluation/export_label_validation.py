"""Export the benchmark's gold labels for independent clinician validation.

Each clinician gets one CSV with every case: the question, the record as the
system sees it (de-identified), and the proposed label with its basis. They
mark each label CONFIRM or CORRECT (with a note) and rate severity. Nothing
here is filled in automatically: expert judgement must come from the experts.

Usage:
    python evaluation/export_label_validation.py --out results/label_validation.csv
    # after two clinicians return their copies:
    python evaluation/export_label_validation.py --summarize v1.csv v2.csv
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import date
from pathlib import Path

from dual_lobe_clinical.privacy import PrivacySession

COLUMNS = ["case_id", "question", "record_as_seen_by_system", "proposed_label", "proposed_summary", "basis",
           "CONFIRM_or_CORRECT", "your_severity(critical/major/minor/none)", "correction_or_note"]


def export(cases_path: str, out: str) -> int:
    suite = json.loads(Path(cases_path).read_text(encoding="utf-8"))
    index_date = date.fromisoformat(suite["index_date"])
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(COLUMNS)
        for c in suite["cases"]:
            session = PrivacySession(index_date=index_date)
            view = session.build_view(c["question"], c["record"])
            session.destroy()
            label = {"unasked_hazard": "HAZARD", "missing_information": "MISSING INFORMATION",
                     "negative_control": "NO HAZARD"}[c["type"]]
            w.writerow([c["id"], view.question, view.render_facts(), label, c["gold"]["summary"],
                        c["gold"].get("basis", ""), "", "", ""])
    return len(suite["cases"])


def summarize(paths: list[str]) -> dict:
    sheets = []
    for p in paths:
        with open(p, newline="", encoding="utf-8") as fh:
            sheets.append({r["case_id"]: r for r in csv.DictReader(fh)})
    ids = sorted(set.intersection(*(set(s) for s in sheets)))
    confirmed_by_all, disputed, blank = [], [], []
    for cid in ids:
        marks = [(s[cid].get("CONFIRM_or_CORRECT") or "").strip().upper() for s in sheets]
        if any(not m for m in marks):
            blank.append(cid)
        elif all(m.startswith("CONF") for m in marks):
            confirmed_by_all.append(cid)
        else:
            disputed.append({"case_id": cid, "notes": [s[cid].get("correction_or_note", "") for s in sheets]})
    return {"validators": len(sheets), "cases": len(ids), "confirmed_by_all": len(confirmed_by_all),
            "disputed": disputed, "not_yet_rated": blank}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", default="benchmarks/clinical/cases.json")
    ap.add_argument("--out", default="results/label_validation.csv")
    ap.add_argument("--summarize", nargs="+", default=None)
    args = ap.parse_args()
    if args.summarize:
        print(json.dumps(summarize(args.summarize), indent=2))
    else:
        n = export(args.cases, args.out)
        print(f"Wrote {n} cases to {args.out}")


if __name__ == "__main__":
    main()
