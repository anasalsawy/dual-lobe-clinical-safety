from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def case_review_id(case_id: str, *, salt: str) -> str:
    return "G-" + hashlib.sha256(f"{salt}|{case_id}".encode()).hexdigest()[:16].upper()


def export_gold_review_cases(
    cases: list[dict[str, Any]],
    *,
    salt: str,
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    packet: list[dict[str, Any]] = []
    key: dict[str, str] = {}
    for case in cases:
        rid = case_review_id(case["case_id"], salt=salt)
        packet.append({
            "review_id": rid,
            "patient_context": case["patient_context"],
            "query": case["query"],
            "proposed_gold": {
                "material_hazard_present": case["gold"]["material_hazard_present"],
                "failure_types": case["gold"]["failure_types"],
                "expected_gate": case["gold"]["expected_gate"],
                "evidence_ids": case["gold"]["evidence_ids"],
                "required_safety_concepts": case["gold"]["required_safety_concepts"],
            },
            "review_fields": {
                "hazard_label_correct": None,
                "negative_control_is_truly_negative": None,
                "expected_gate_appropriate": None,
                "evidence_supports_gold": None,
                "wording_is_clinically_plausible": None,
                "suggested_changes": "",
                "reviewer_confidence": "unrated",
            },
        })
        key[rid] = case["case_id"]
    return packet, key


def validate_gold_reviews(records: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    seen: set[tuple[str, str]] = set()
    bool_fields = (
        "hazard_label_correct",
        "negative_control_is_truly_negative",
        "expected_gate_appropriate",
        "evidence_supports_gold",
        "wording_is_clinically_plausible",
    )
    for i, row in enumerate(records):
        rid = str(row.get("review_id") or "").strip()
        reviewer = str(row.get("reviewer_id") or "").strip()
        prefix = rid or f"record[{i}]"
        if not rid:
            errors.append(f"{prefix}: review_id required")
        if not reviewer:
            errors.append(f"{prefix}: reviewer_id required")
        key=(rid,reviewer)
        if key in seen:
            errors.append(f"{prefix}: duplicate reviewer/review_id")
        seen.add(key)
        for field in bool_fields:
            if not isinstance(row.get(field), bool):
                errors.append(f"{prefix}: {field} must be boolean")
        if row.get("reviewer_confidence") not in {"low","moderate","high"}:
            errors.append(f"{prefix}: invalid reviewer_confidence")
    return errors


def gold_review_consensus(
    records: list[dict[str, Any]],
    *,
    minimum_reviewers: int = 2,
) -> dict[str, dict[str, Any]]:
    errors=validate_gold_reviews(records)
    if errors:
        raise ValueError("gold review validation failed:\n- "+"\n- ".join(errors))

    fields=(
        "hazard_label_correct",
        "negative_control_is_truly_negative",
        "expected_gate_appropriate",
        "evidence_supports_gold",
        "wording_is_clinically_plausible",
    )
    grouped: dict[str,list[dict[str,Any]]]=defaultdict(list)
    for row in records:
        grouped[row["review_id"]].append(row)

    out={}
    for rid,items in grouped.items():
        if len(items)<minimum_reviewers:
            continue
        result={"reviewer_count":len(items),"requires_adjudication":False}
        for field in fields:
            yes=sum(bool(x[field]) for x in items)
            no=len(items)-yes
            if yes==no:
                result[field]=None
                result["requires_adjudication"]=True
            else:
                result[field]=yes>no
        result["approved_for_freeze"]=(
            not result["requires_adjudication"]
            and all(result[field] is True for field in fields)
        )
        out[rid]=result
    return out
