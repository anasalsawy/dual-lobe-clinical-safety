"""Deterministic privacy audit over the benchmark (no model calls).

For every case, the audit builds the exact prompt Lobe A would receive, then
measures:

* leakage: planted identifiers still present in A's prompt, split into
  (a) leaks the deterministic layer should have caught (defects), and
  (b) identifiers the case marks as needing the local-B residual sweep;
* utility: non-identifying record values (drugs, doses, labs, notes without
  dates) that reach A unchanged. Over-redaction harms clinical reasoning.
* crypto-shredding: after destroy(), tokens cannot be resolved.

Usage:
    python evaluation/privacy_audit.py [--cases benchmarks/clinical/cases.json] [--out results/privacy_audit.json]
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path

from dual_lobe_clinical.privacy import (
    _FIELD_CATEGORY,
    _IDENTIFYING_CONTAINERS,
    _DATE_PATTERNS,
    PrivacySession,
    VaultDestroyed,
    _field_key,
)
from dual_lobe_clinical.prompts import A_CLINICAL_TASK, DEIDENTIFICATION_NOTE


def clinical_leaves(value, path=""):
    """Non-identifying string leaves of a record (what should survive)."""
    if isinstance(value, dict):
        for k, v in value.items():
            key = _field_key(k)
            if key in _FIELD_CATEGORY or key in _IDENTIFYING_CONTAINERS:
                continue
            yield from clinical_leaves(v, f"{path}.{k}" if path else k)
    elif isinstance(value, list):
        for i, v in enumerate(value):
            yield from clinical_leaves(v, f"{path}[{i}]")
    elif isinstance(value, (str, int, float)) and str(value).strip():
        yield path, str(value)


def audit_case(case: dict, index_date: date) -> dict:
    session = PrivacySession(index_date=index_date)
    view = session.build_view(case["question"], case["record"])
    prompt = A_CLINICAL_TASK.format(deid=DEIDENTIFICATION_NOTE, question=view.question, facts=view.render_facts())
    low = prompt.casefold()

    planted = case.get("phi", [])
    sweep_expected = set(case.get("phi_needs_residual_sweep", []))
    leaked = [p for p in planted if p.casefold() in low]
    defects = [p for p in leaked if p not in sweep_expected]
    residual = [p for p in leaked if p in sweep_expected]

    preserved = changed = 0
    over_redacted: list[str] = []
    for path, text in clinical_leaves(case["record"]):
        # Leaves containing a person's identifier or a calendar date are
        # expected to change.
        if any(p.casefold() in text.casefold() for p in planted) or any(pt.search(text) for _, pt in _DATE_PATTERNS):
            continue
        if text in prompt:
            preserved += 1
        else:
            changed += 1
            over_redacted.append(f"{path}: {text}")

    tokens = re.findall(r"\[[A-Z]+#[0-9a-f]{6}\]", prompt)
    receipt = session.destroy()
    shredded = False
    try:
        session.rehydrate(tokens[0] if tokens else "[NAME#000000]")
    except VaultDestroyed:
        shredded = True

    return {
        "id": case["id"],
        "planted": len(planted),
        "leaked_defects": defects,
        "residual_for_local_sweep": residual,
        "clinical_values_preserved": preserved,
        "clinical_values_altered": over_redacted,
        "identifiers_by_category": receipt.identifiers_protected,
        "detection_sources": receipt.detection_sources,
        "crypto_shredded": shredded and receipt.key_destroyed,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", default="benchmarks/clinical/cases.json")
    ap.add_argument("--out", default="results/privacy_audit.json")
    args = ap.parse_args()
    suite = json.loads(Path(args.cases).read_text(encoding="utf-8"))
    index_date = date.fromisoformat(suite["index_date"])
    rows = [audit_case(c, index_date) for c in suite["cases"]]

    planted = sum(r["planted"] for r in rows)
    defects = sum(len(r["leaked_defects"]) for r in rows)
    residual = sum(len(r["residual_for_local_sweep"]) for r in rows)
    preserved = sum(r["clinical_values_preserved"] for r in rows)
    altered = sum(len(r["clinical_values_altered"]) for r in rows)
    summary = {
        "cases": len(rows),
        "identifiers_planted": planted,
        "removed_by_deterministic_layer": planted - defects - residual,
        "leaked_defects": defects,
        "left_for_local_b_sweep": residual,
        "clinical_values_preserved": preserved,
        "clinical_values_altered": altered,
        "all_sessions_crypto_shredded": all(r["crypto_shredded"] for r in rows),
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps({"summary": summary, "cases": rows}, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    for r in rows:
        if r["leaked_defects"] or r["residual_for_local_sweep"] or r["clinical_values_altered"]:
            print(r["id"], "defects:", r["leaked_defects"], "residual:", r["residual_for_local_sweep"],
                  "altered:", r["clinical_values_altered"])


if __name__ == "__main__":
    main()
