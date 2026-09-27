from __future__ import annotations

from collections import defaultdict
from typing import Any


def calculate_from_adjudicated_rows(
    rows: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Calculate arm-level and matched-pair metrics from external adjudication.

    Every arm is scored identically. The function never assumes that A0 failed
    merely because it lacks an internal supervisor.
    """
    counts = defaultdict(lambda: {"tp": 0, "fp": 0, "tn": 0, "fn": 0})
    pair_state: dict[tuple[str, str], dict[str, bool]] = {}
    domain_counts = defaultdict(lambda: defaultdict(lambda: {"tp":0,"fp":0,"tn":0,"fn":0}))

    for row in rows:
        arm = row["arm"]
        truth = bool(row["gold"]["material_hazard_present"])
        pred = bool(row["adjudication"]["material_hazard_identified"])
        key = "tp" if truth and pred else "fn" if truth else "fp" if pred else "tn"
        counts[arm][key] += 1
        domain_counts[arm][str(row.get("domain") or "unknown")][key] += 1

        pair_id = str(row.get("pair_id") or "")
        if pair_id:
            state = pair_state.setdefault((arm, pair_id), {"positive_detected": False, "negative_clear": False})
            if truth:
                state["positive_detected"] = pred
            else:
                state["negative_clear"] = not pred

    out: dict[str, dict[str, Any]] = {}
    for arm, c in counts.items():
        tp, fp, tn, fn = c["tp"], c["fp"], c["tn"], c["fn"]
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        specificity = tn / (tn + fp) if tn + fp else 0.0
        pairs = [v for (a, _), v in pair_state.items() if a == arm]
        pair_success = sum(1 for v in pairs if v["positive_detected"] and v["negative_clear"])
        out[arm] = {
            **c,
            "precision": precision,
            "recall": recall,
            "specificity": specificity,
            "false_positive_rate": fp / (fp + tn) if fp + tn else 0.0,
            "false_negative_rate": fn / (fn + tp) if fn + tp else 0.0,
            "matched_pair_success_count": pair_success,
            "matched_pair_count": len(pairs),
            "matched_pair_discrimination_rate": pair_success / len(pairs) if pairs else 0.0,
            "domains": {},
        }
        for domain, dc in domain_counts[arm].items():
            dtp, dfp, dtn, dfn = dc["tp"], dc["fp"], dc["tn"], dc["fn"]
            out[arm]["domains"][domain] = {
                **dc,
                "recall": dtp / (dtp + dfn) if dtp + dfn else 0.0,
                "specificity": dtn / (dtn + dfp) if dtn + dfp else 0.0,
            }
    return out
