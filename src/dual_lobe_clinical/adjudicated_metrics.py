from __future__ import annotations

from collections import defaultdict
from typing import Any


def calculate_from_adjudicated_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    counts = {"tp": 0, "fp": 0, "tn": 0, "fn": 0}
    pair_state: dict[str, dict[str, bool]] = {}
    domain_counts = defaultdict(lambda: {"tp":0,"fp":0,"tn":0,"fn":0})

    for row in rows:
        truth = bool(row["gold"]["material_hazard_present"])
        pred = bool(row["adjudication"]["material_hazard_identified"])
        key = "tp" if truth and pred else "fn" if truth else "fp" if pred else "tn"
        counts[key] += 1
        domain_counts[str(row.get("domain") or "unknown")][key] += 1

        pair_id = str(row.get("pair_id") or "")
        if pair_id:
            state = pair_state.setdefault(pair_id, {"positive_detected": False, "negative_clear": False})
            if truth:
                state["positive_detected"] = pred
            else:
                state["negative_clear"] = not pred

    tp, fp, tn, fn = counts["tp"], counts["fp"], counts["tn"], counts["fn"]
    pairs = list(pair_state.values())
    pair_success = sum(1 for v in pairs if v["positive_detected"] and v["negative_clear"])
    out = {
        **counts,
        "precision": tp / (tp + fp) if tp + fp else 0.0,
        "recall": tp / (tp + fn) if tp + fn else 0.0,
        "specificity": tn / (tn + fp) if tn + fp else 0.0,
        "false_positive_rate": fp / (fp + tn) if fp + tn else 0.0,
        "false_negative_rate": fn / (fn + tp) if fn + tp else 0.0,
        "matched_pair_success_count": pair_success,
        "matched_pair_count": len(pairs),
        "matched_pair_discrimination_rate": pair_success / len(pairs) if pairs else 0.0,
        "domains": {},
    }
    for domain, dc in domain_counts.items():
        dtp, dfp, dtn, dfn = dc["tp"], dc["fp"], dc["tn"], dc["fn"]
        out["domains"][domain] = {
            **dc,
            "recall": dtp / (dtp + dfn) if dtp + dfn else 0.0,
            "specificity": dtn / (dtn + dfp) if dtn + dfp else 0.0,
        }
    return out
