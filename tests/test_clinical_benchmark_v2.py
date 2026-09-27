from pathlib import Path

from dual_lobe_clinical.benchmark_validation import load_jsonl, validate_cases
from dual_lobe_clinical.evidence import FrozenEvidenceStore


def test_v03_benchmark_has_48_cases_and_24_pairs():
    cases = load_jsonl(Path("benchmarks/clinical_cases_v2.jsonl"))
    assert len(cases) == 48
    assert len({c["pair_id"] for c in cases}) == 24


def test_v02_benchmark_is_structurally_valid_against_evidence_corpus():
    cases = load_jsonl(Path("benchmarks/clinical_cases_v2.jsonl"))
    evidence = FrozenEvidenceStore.load_json("evidence/evidence_manifest.json")
    ids = {r.evidence_id for r in evidence.records()}
    assert validate_cases(cases, evidence_ids=ids, strict_metadata=True) == []


def test_every_positive_has_authoritative_evidence_and_safety_concepts():
    cases = load_jsonl(Path("benchmarks/clinical_cases_v2.jsonl"))
    positives = [c for c in cases if c["gold"]["material_hazard_present"]]
    assert positives
    assert all(c["gold"]["evidence_ids"] for c in positives)
    assert all(c["gold"]["required_safety_concepts"] for c in positives)


def test_every_pair_has_exactly_one_positive_and_one_negative():
    cases = load_jsonl(Path("benchmarks/clinical_cases_v2.jsonl"))
    by_pair = {}
    for case in cases:
        by_pair.setdefault(case["pair_id"], []).append(case)
    for members in by_pair.values():
        assert len(members) == 2
        truths = [m["gold"]["material_hazard_present"] for m in members]
        assert sorted(truths) == [False, True]


def test_benchmark_spans_all_seed_evidence_domains():
    cases = load_jsonl(Path("benchmarks/clinical_cases_v2.jsonl"))
    domains = {c["domain"] for c in cases}
    assert domains == {
        "anticoagulant_nsaid",
        "nsaid_renal",
        "metformin_renal",
        "beta_lactam_allergy",
        "pregnancy_nsaid",
        "aspirin_sensitive_asthma",
        "sepsis_red_flags",
        "acetaminophen_hepatic",
        "citalopram_qt_electrolyte",
        "glyburide_geriatric",
        "methotrexate_infection",
        "stroke_red_flags",
    }
