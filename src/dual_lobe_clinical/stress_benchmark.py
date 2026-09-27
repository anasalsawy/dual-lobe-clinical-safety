from __future__ import annotations

from typing import Any


VALID_GATES = {"pass","warn","revise","block","escalate","insufficient_evidence"}


def validate_stress_cases(cases: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    for case in cases:
        cid = str(case.get("case_id") or "")
        if not cid:
            errors.append("case_id required")
            continue
        if cid in seen:
            errors.append(f"{cid}: duplicate case_id")
        seen.add(cid)
        if case.get("expected_gate") not in VALID_GATES:
            errors.append(f"{cid}: invalid expected_gate")
        if not case.get("failure_types"):
            errors.append(f"{cid}: failure_types required")
        if not str(case.get("rationale") or "").strip():
            errors.append(f"{cid}: rationale required")
    return errors
