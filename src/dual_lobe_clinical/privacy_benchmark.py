from __future__ import annotations

from collections import defaultdict
from typing import Any


VALID_PRIVACY_FAILURES = {"F19","F20","F21","F22","F23"}
VALID_DECISIONS = {"allow","block"}


def validate_privacy_cases(cases: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    pairs: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: set[str] = set()

    for case in cases:
        cid = str(case.get("case_id") or "")
        if not cid:
            errors.append("case_id required")
            continue
        if cid in seen:
            errors.append(f"{cid}: duplicate case_id")
        seen.add(cid)

        pair_id = str(case.get("pair_id") or "")
        if not pair_id:
            errors.append(f"{cid}: pair_id required")
        else:
            pairs[pair_id].append(case)

        expected = case.get("expected") or {}
        violation = expected.get("violation")
        if not isinstance(violation, bool):
            errors.append(f"{cid}: expected.violation must be boolean")

        failures = expected.get("failure_types") or []
        invalid = [f for f in failures if f not in VALID_PRIVACY_FAILURES]
        if invalid:
            errors.append(f"{cid}: invalid privacy failure types {invalid}")

        if violation and not failures:
            errors.append(f"{cid}: positive privacy case requires failure_types")
        if not violation and failures:
            errors.append(f"{cid}: negative privacy case cannot carry failure_types")

        decision = expected.get("decision")
        if decision not in VALID_DECISIONS:
            errors.append(f"{cid}: decision must be allow|block")

    for pair_id, members in pairs.items():
        if len(members) != 2:
            errors.append(f"{pair_id}: expected exactly two paired cases")
            continue
        truths = sorted(bool(m["expected"]["violation"]) for m in members)
        if truths != [False, True]:
            errors.append(f"{pair_id}: pair must contain one violation and one safe control")

    return errors
