from __future__ import annotations

import math
from collections import defaultdict
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


def exact_mcnemar_pvalue(b: int, c: int) -> float:
    """Two-sided exact McNemar/binomial p-value for discordant matched outcomes."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / (2 ** n)
    return min(1.0, 2.0 * tail)


def arm_binary_map(rows: list[dict[str, Any]]) -> dict[str, dict[str, bool]]:
    out: dict[str, dict[str, bool]] = defaultdict(dict)
    for row in rows:
        out[row["arm"]][row["case_id"]] = bool(
            row["adjudication"]["material_hazard_identified"]
        )
    return dict(out)


def paired_arm_comparison(
    rows: list[dict[str, Any]],
    *,
    arm_a: str,
    arm_b: str,
) -> dict[str, Any]:
    by_arm = arm_binary_map(rows)
    a = by_arm.get(arm_a, {})
    b = by_arm.get(arm_b, {})
    common = sorted(set(a) & set(b))
    b_only = sum(1 for cid in common if b[cid] and not a[cid])
    a_only = sum(1 for cid in common if a[cid] and not b[cid])
    return {
        "arm_a": arm_a,
        "arm_b": arm_b,
        "paired_case_count": len(common),
        "arm_b_positive_arm_a_negative": b_only,
        "arm_a_positive_arm_b_negative": a_only,
        "exact_mcnemar_p": exact_mcnemar_pvalue(b_only, a_only),
    }


def add_confidence_intervals(metrics: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for arm, data in metrics.items():
        d = dict(data)
        tp, fp, tn, fn = d["tp"], d["fp"], d["tn"], d["fn"]
        d["recall_ci95"] = wilson_interval(tp, tp + fn)
        d["specificity_ci95"] = wilson_interval(tn, tn + fp)
        d["precision_ci95"] = wilson_interval(tp, tp + fp)
        pair_success = int(d.get("matched_pair_success_count", 0))
        pair_total = int(d.get("matched_pair_count", 0))
        d["matched_pair_discrimination_ci95"] = wilson_interval(pair_success, pair_total)
        out[arm] = d
    return out
