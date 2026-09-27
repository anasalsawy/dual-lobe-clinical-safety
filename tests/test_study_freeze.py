from types import SimpleNamespace
import pytest
from dual_lobe_clinical.benchmark_runner import validate_study_inputs


def args(mode, guardian_manifest="guardian/guardian_manifest.json"):
    return SimpleNamespace(study_mode=mode,guardian_manifest=str(guardian_manifest))


def paired_cases(*, development_only=False):
    return [
        {"case_id":"P","pair_id":"PAIR","patient_context":{},"query":"q",
         "gold":{"material_hazard_present":True,"failure_types":["F01"],"expected_gate":"block"},
         "development_only":development_only},
        {"case_id":"N","pair_id":"PAIR","patient_context":{},"query":"q",
         "gold":{"material_hazard_present":False,"failure_types":[],"expected_gate":"pass"},
         "development_only":development_only},
    ]


def test_primary_study_rejects_development_cases():
    with pytest.raises(ValueError,match="development_only"):
        validate_study_inputs(args("primary"),paired_cases(development_only=True))


def test_development_mode_allows_development_cases():
    validate_study_inputs(args("development"),paired_cases(development_only=True))
