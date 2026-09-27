from types import SimpleNamespace

import pytest

from dual_lobe_clinical.benchmark_runner import validate_study_inputs


def args(mode, evidence, guardian_manifest="guardian/guardian_manifest.json"):
    return SimpleNamespace(
        study_mode=mode,
        evidence=str(evidence),
        guardian_manifest=str(guardian_manifest),
    )


def paired_cases(*, development_only=False):
    return [
        {
            "case_id": "P",
            "pair_id": "PAIR",
            "patient_context": {},
            "query": "q",
            "gold": {
                "material_hazard_present": True,
                "failure_types": ["F01"],
                "expected_gate": "block",
            },
            "development_only": development_only,
        },
        {
            "case_id": "N",
            "pair_id": "PAIR",
            "patient_context": {},
            "query": "q",
            "gold": {
                "material_hazard_present": False,
                "failure_types": [],
                "expected_gate": "pass",
            },
            "development_only": development_only,
        },
    ]


def write_evidence(path, records):
    path.write_text('{"records": ' + __import__("json").dumps(records) + '}', encoding="utf-8")


def test_primary_study_rejects_development_cases(tmp_path):
    evidence = tmp_path / "evidence.json"
    write_evidence(evidence, [{
        "evidence_id": "E1",
        "source": "synthetic",
        "title": "x",
        "version_or_date": "v1",
        "excerpt": "x",
        "tags": [],
    }])
    with pytest.raises(ValueError, match="development_only"):
        validate_study_inputs(args("primary", evidence), paired_cases(development_only=True))


def test_primary_study_rejects_empty_evidence(tmp_path):
    evidence = tmp_path / "evidence.json"
    write_evidence(evidence, [])
    with pytest.raises(ValueError, match="empty evidence corpus"):
        validate_study_inputs(args("primary", evidence), paired_cases())


def test_development_mode_allows_empty_evidence(tmp_path):
    evidence = tmp_path / "evidence.json"
    write_evidence(evidence, [])
    validate_study_inputs(args("development", evidence), paired_cases(development_only=True))
