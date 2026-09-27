from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from urllib.parse import urlparse


ALLOWED_SOURCE_TYPES = {
    "regulatory_label",
    "government_safety_communication",
    "government_clinical_guidance",
    "professional_guideline",
    "systematic_review",
    "peer_reviewed_study",
}


def _valid_iso_date(value: str) -> bool:
    try:
        date.fromisoformat(value)
        return True
    except Exception:
        return False


def validate_evidence_manifest(
    path: str | Path,
    *,
    require_primary_frozen: bool = False,
) -> list[str]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    errors: list[str] = []

    if require_primary_frozen and raw.get("status") != "primary_frozen":
        errors.append("primary study requires evidence manifest status=primary_frozen")

    if not str(raw.get("corpus_version") or "").strip():
        errors.append("corpus_version is required")

    records = raw.get("records")
    if not isinstance(records, list):
        return errors + ["records must be a list"]

    seen: set[str] = set()
    for i, record in enumerate(records):
        if not isinstance(record, dict):
            errors.append(f"record[{i}] must be an object")
            continue
        eid = str(record.get("evidence_id") or "").strip()
        prefix = eid or f"record[{i}]"
        if not eid:
            errors.append(f"{prefix}: evidence_id required")
        elif eid in seen:
            errors.append(f"{prefix}: duplicate evidence_id")
        seen.add(eid)

        for field in (
            "source", "title", "version_or_date", "excerpt",
            "source_url", "source_org", "source_type",
            "effective_date", "accessed_at", "source_locator",
        ):
            if not str(record.get(field) or "").strip():
                errors.append(f"{prefix}: {field} required")

        url = str(record.get("source_url") or "")
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.netloc:
            errors.append(f"{prefix}: source_url must be an absolute https URL")

        source_type = str(record.get("source_type") or "")
        if source_type and source_type not in ALLOWED_SOURCE_TYPES:
            errors.append(f"{prefix}: unsupported source_type {source_type!r}")

        for field in ("effective_date", "accessed_at"):
            value = str(record.get(field) or "")
            if value and not _valid_iso_date(value):
                errors.append(f"{prefix}: {field} must be YYYY-MM-DD")

        tags = record.get("tags")
        if not isinstance(tags, list) or not tags:
            errors.append(f"{prefix}: at least one retrieval tag required")

    return errors


def assert_valid_evidence_manifest(
    path: str | Path,
    *,
    require_primary_frozen: bool = False,
) -> None:
    errors = validate_evidence_manifest(
        path,
        require_primary_frozen=require_primary_frozen,
    )
    if errors:
        raise ValueError("evidence manifest validation failed:\n- " + "\n- ".join(errors))
