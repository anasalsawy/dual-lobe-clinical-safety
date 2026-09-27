from __future__ import annotations

import math
from typing import Any


def wilson_interval(successes: int, total: int, *, z: float = 1.959963984540054) -> tuple[float, float]:
    if total <= 0:
        return (0.0, 0.0)
    p = successes / total
    z2 = z * z
    denom = 1.0 + z2 / total
    center = (p + z2 / (2 * total)) / denom
    half = z * math.sqrt((p * (1 - p) + z2 / (4 * total)) / total) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def add_confidence_intervals(metrics: dict[str, Any]) -> dict[str, Any]:
    d = dict(metrics)
    tp, fp, tn, fn = d["tp"], d["fp"], d["tn"], d["fn"]
    d["recall_ci95"] = wilson_interval(tp, tp + fn)
    d["specificity_ci95"] = wilson_interval(tn, tn + fp)
    d["precision_ci95"] = wilson_interval(tp, tp + fp)
    pair_success = int(d.get("matched_pair_success_count", 0))
    pair_total = int(d.get("matched_pair_count", 0))
    d["matched_pair_discrimination_ci95"] = wilson_interval(pair_success, pair_total)
    return d
