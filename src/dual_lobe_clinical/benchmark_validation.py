from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .schemas import Decision, FailureType

VALID_FAILURES = {x.value for x in FailureType}
VALID_GATES = {x.value for x in Decision}


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows = []
    for lineno, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON on line {lineno}: {exc}") from exc
    return rows


def validate_cases(cases: list[dict[str, Any]], *, require_pairs: bool = True, strict_metadata: bool = False) -> list[str]:
    errors = []
    ids = [str(x.get("case_id", "")) for x in cases]
    dupes = [k for k, v in Counter(ids).items() if k and v > 1]
    if dupes:
        errors.append(f"duplicate case_id: {sorted(dupes)}")
    if any(not x for x in ids):
        errors.append("every case requires case_id")

    pairs = defaultdict(list)
    for case in cases:
        cid = str(case.get("case_id") or "<missing>")
        if not isinstance(case.get("patient_context"), dict):
            errors.append(f"{cid}: patient_context must be an object")
        if not str(case.get("query") or "").strip():
            errors.append(f"{cid}: query required")

        if strict_metadata:
            if not str(case.get("domain") or "").strip():
                errors.append(f"{cid}: domain required")
            if str(case.get("difficulty") or "") not in {"easy", "moderate", "hard"}:
                errors.append(f"{cid}: difficulty must be easy|moderate|hard")

        gold = case.get("gold")
        if not isinstance(gold, dict):
            errors.append(f"{cid}: gold must be an object")
            continue

        hazard = gold.get("material_hazard_present")
        if not isinstance(hazard, bool):
            errors.append(f"{cid}: material_hazard_present must be boolean")

        failures = gold.get("failure_types") or []
        bad = [x for x in failures if x not in VALID_FAILURES]
        if bad:
            errors.append(f"{cid}: invalid failure types {bad}")
        if hazard is False and failures:
            errors.append(f"{cid}: negative control cannot have gold failure types")
        if hazard is True and not failures:
            errors.append(f"{cid}: positive case requires at least one failure type")

        gate = gold.get("expected_gate")
        if gate not in VALID_GATES:
            errors.append(f"{cid}: invalid expected_gate {gate!r}")

        concepts = gold.get("required_safety_concepts") or []
        if strict_metadata and hazard is True and not concepts:
            errors.append(f"{cid}: positive case requires required_safety_concepts")

        pair_id = case.get("pair_id")
        if pair_id:
            pairs[str(pair_id)].append(case)
        elif require_pairs:
            errors.append(f"{cid}: pair_id required")

    if require_pairs:
        for pair_id, members in pairs.items():
            truths = [bool(x["gold"]["material_hazard_present"]) for x in members if isinstance(x.get("gold"), dict)]
            if len(members) < 2:
                errors.append(f"{pair_id}: matched pair has fewer than 2 cases")
            if not (any(truths) and not all(truths)):
                errors.append(f"{pair_id}: matched pair must include positive and negative cases")
            if strict_metadata:
                domains = {str(x.get("domain") or "") for x in members}
                if len(domains) != 1:
                    errors.append(f"{pair_id}: matched pair must remain within one domain")
    return errors


def assert_valid_cases(cases: list[dict[str, Any]], *, require_pairs: bool = True, strict_metadata: bool = False) -> None:
    errors = validate_cases(cases, require_pairs=require_pairs, strict_metadata=strict_metadata)
    if errors:
        raise ValueError("benchmark validation failed:\n- " + "\n- ".join(errors))
