import json

import pytest

from dual_lobe_clinical.evidence import FrozenEvidenceStore
from dual_lobe_clinical.evidence_validation import (
    assert_valid_evidence_manifest,
    validate_evidence_manifest,
)


def test_repository_evidence_seed_has_complete_provenance():
    assert validate_evidence_manifest("evidence/evidence_manifest.json") == []
    store = FrozenEvidenceStore.load_json("evidence/evidence_manifest.json")
    assert len(store.records()) >= 5
    assert all(r.source_url.startswith("https://") for r in store.records())
    assert all(r.source_org for r in store.records())


def test_repository_seed_is_not_falsely_marked_primary_frozen():
    with pytest.raises(ValueError, match="primary_frozen"):
        assert_valid_evidence_manifest(
            "evidence/evidence_manifest.json",
            require_primary_frozen=True,
        )


def test_missing_provenance_is_rejected(tmp_path):
    p = tmp_path / "evidence.json"
    p.write_text(json.dumps({
        "corpus_version": "x",
        "status": "development_validated",
        "records": [{
            "evidence_id": "E1",
            "source": "source",
            "title": "title",
            "version_or_date": "v1",
            "excerpt": "claim",
            "tags": ["x"]
        }]
    }), encoding="utf-8")
    errors = validate_evidence_manifest(p)
    assert any("source_url required" in x for x in errors)
    assert any("source_org required" in x for x in errors)


def test_duplicate_evidence_ids_are_rejected(tmp_path):
    base = {
        "evidence_id": "E1",
        "source": "s",
        "title": "t",
        "version_or_date": "v",
        "excerpt": "claim",
        "tags": ["x"],
        "source_url": "https://example.org/x",
        "source_org": "org",
        "source_type": "peer_reviewed_study",
        "effective_date": "2026-01-01",
        "accessed_at": "2026-09-27",
        "source_locator": "section"
    }
    p = tmp_path / "evidence.json"
    p.write_text(json.dumps({
        "corpus_version": "x",
        "status": "development_validated",
        "records": [base, dict(base)]
    }), encoding="utf-8")
    errors = validate_evidence_manifest(p)
    assert any("duplicate evidence_id" in x for x in errors)
