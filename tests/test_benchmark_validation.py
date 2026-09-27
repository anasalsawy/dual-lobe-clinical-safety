from pathlib import Path

import pytest

from dual_lobe_clinical.benchmark_validation import (
    assert_valid_cases,
    load_jsonl,
    validate_cases,
)


def test_development_benchmark_is_structurally_valid():
    cases = load_jsonl(Path("benchmarks/clinical_cases_v1.jsonl"))
    assert validate_cases(cases) == []


def test_duplicate_ids_are_rejected():
    case = {
        "case_id": "X",
        "pair_id": "P",
        "patient_context": {},
        "query": "q",
        "gold": {
            "material_hazard_present": True,
            "failure_types": ["F01"],
            "expected_gate": "block",
        },
    }
    negative = {
        **case,
        "gold": {
            "material_hazard_present": False,
            "failure_types": [],
            "expected_gate": "pass",
        },
    }
    errors = validate_cases([case, negative])
    assert any("duplicate case_id" in x for x in errors)


def test_unpaired_positive_is_rejected():
    cases = [{
        "case_id": "P1",
        "pair_id": "PAIR",
        "patient_context": {},
        "query": "q",
        "gold": {
            "material_hazard_present": True,
            "failure_types": ["F01"],
            "expected_gate": "block",
        },
    }]
    with pytest.raises(ValueError):
        assert_valid_cases(cases)


def test_negative_control_cannot_have_gold_failure():
    cases = [{
        "case_id": "N1",
        "pair_id": "PAIR",
        "patient_context": {},
        "query": "q",
        "gold": {
            "material_hazard_present": False,
            "failure_types": ["F01"],
            "expected_gate": "pass",
        },
    },{
        "case_id": "P1",
        "pair_id": "PAIR",
        "patient_context": {},
        "query": "q",
        "gold": {
            "material_hazard_present": True,
            "failure_types": ["F01"],
            "expected_gate": "block",
        },
    }]
    errors = validate_cases(cases)
    assert any("negative control cannot have gold failure types" in x for x in errors)
