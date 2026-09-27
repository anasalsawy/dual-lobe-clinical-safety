import json
from pathlib import Path

from dual_lobe_clinical.privacy_benchmark import validate_privacy_cases


def load_cases():
    return [
        json.loads(line)
        for line in Path("benchmarks/privacy_cases_v1.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_privacy_benchmark_has_five_matched_pairs():
    cases = load_cases()
    assert len(cases) == 10
    assert len({c["pair_id"] for c in cases}) == 5


def test_privacy_benchmark_is_structurally_valid():
    assert validate_privacy_cases(load_cases()) == []


def test_privacy_positives_cover_all_new_failure_classes():
    cases = load_cases()
    failures = {
        f
        for c in cases
        if c["expected"]["violation"]
        for f in c["expected"]["failure_types"]
    }
    assert failures == {"F19","F20","F21","F22","F23"}
