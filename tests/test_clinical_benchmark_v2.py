from pathlib import Path
from dual_lobe_clinical.benchmark_validation import load_jsonl, validate_cases


def test_v04_benchmark_has_48_cases_and_24_pairs():
    cases=load_jsonl(Path("benchmarks/clinical_cases_v2.jsonl"))
    assert len(cases)==48
    assert len({c["pair_id"] for c in cases})==24


def test_benchmark_is_structurally_valid():
    cases=load_jsonl(Path("benchmarks/clinical_cases_v2.jsonl"))
    assert validate_cases(cases,strict_metadata=True)==[]


def test_every_positive_has_safety_concepts():
    cases=load_jsonl(Path("benchmarks/clinical_cases_v2.jsonl"))
    positives=[c for c in cases if c["gold"]["material_hazard_present"]]
    assert positives
    assert all(c["gold"]["required_safety_concepts"] for c in positives)


def test_every_pair_has_exactly_one_positive_and_one_negative():
    cases=load_jsonl(Path("benchmarks/clinical_cases_v2.jsonl"))
    by_pair={}
    for case in cases:
        by_pair.setdefault(case["pair_id"],[]).append(case)
    for members in by_pair.values():
        assert len(members)==2
        assert sorted(m["gold"]["material_hazard_present"] for m in members)==[False,True]
