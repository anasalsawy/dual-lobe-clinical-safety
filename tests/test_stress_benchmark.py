import json
from pathlib import Path

from dual_lobe_clinical.stress_benchmark import validate_stress_cases


def load_cases():
    return [
        json.loads(line)
        for line in Path("benchmarks/stress_cases_v1.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_stress_set_is_valid():
    assert validate_stress_cases(load_cases()) == []


def test_stress_set_contains_fail_closed_and_escalation_targets():
    gates = {c["expected_gate"] for c in load_cases()}
    assert "insufficient_evidence" in gates
    assert "escalate" in gates
    assert "block" in gates


def test_correlated_failure_case_exists():
    assert any("F14" in c["failure_types"] for c in load_cases())
