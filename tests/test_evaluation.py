import json
import sys
from argparse import Namespace
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evaluation"))

import privacy_audit  # noqa: E402
import run_study  # noqa: E402
import score  # noqa: E402
from clinical_fakes import FakeProviders, configure_env  # noqa: E402

CASES = ROOT / "benchmarks" / "clinical" / "cases.json"
SUITE = json.loads(CASES.read_text())


def test_benchmark_is_well_formed():
    ids = [c["id"] for c in SUITE["cases"]]
    assert len(ids) == len(set(ids)) == 29
    types = {c["type"] for c in SUITE["cases"]}
    assert types == {"unasked_hazard", "missing_information", "negative_control"}
    for c in SUITE["cases"]:
        assert c["phi"], c["id"]
        if c["type"] != "negative_control":
            assert c["gold"]["terms"] and c["gold"]["fact_paths"], c["id"]


def test_gold_fact_paths_exist_in_the_deidentified_view():
    from dual_lobe_clinical.privacy import PrivacySession

    for c in SUITE["cases"]:
        view = PrivacySession(index_date=date(2026, 9, 28)).build_view(c["question"], c["record"])
        paths = set(view.fact_paths().values())
        for g in c["gold"]["fact_paths"]:
            assert any(p == g or p.startswith(g) for p in paths), (c["id"], g)


def test_privacy_audit_has_no_deterministic_defects():
    rows = [privacy_audit.audit_case(c, date(2026, 9, 28)) for c in SUITE["cases"]]
    assert all(not r["leaked_defects"] for r in rows)
    assert all(not r["clinical_values_altered"] for r in rows)
    assert all(r["crypto_shredded"] for r in rows)


def test_wilson_and_mcnemar():
    lo, hi = score.wilson(0, 10)
    assert lo == 0 and 0.27 < hi < 0.29
    assert score.mcnemar_exact(0, 0) == 1.0
    assert score.mcnemar_exact(8, 0) == pytest.approx(2 / 256)


def test_term_matching_is_word_prefix():
    assert score.mentions("Risk of acute kidney injury.", ["kidney"])
    assert not score.mentions("adrenal crisis", ["renal"])  # no mid-word matches


def test_interrupting_hit_by_fact_path_or_term():
    gold = {"fact_paths": ["labs.eGFR"], "terms": ["renal"]}
    row = {"fact_paths": {"F4": "labs.eGFR"},
           "findings": [{"interrupting": True, "patient_evidence": ["[F4]"], "statement": "x"}]}
    assert score.interrupting_hits(row, gold)
    row["findings"][0]["interrupting"] = False
    assert not score.interrupting_hits(row, gold)


@pytest.mark.asyncio
async def test_harness_runs_end_to_end_with_scripted_models(monkeypatch, tmp_path):
    configure_env(monkeypatch)
    fp = FakeProviders()
    fp.install(monkeypatch)
    fp.scan = {"context_summary": "", "hazards": []}
    fp.audit = {"answer_verdict": {"deception_level": "GREEN", "rationale": "ok", "handoff": {}}, "findings": []}
    fp.verifier = fp.audit
    args = Namespace(cases=str(CASES), arms=["a_only", "answer_verifier", "dual_lobe"], repeats=1,
                     only=["H01", "N01"], out_dir=str(tmp_path))
    out = await run_study.run(args)
    rows = [json.loads(x) for x in out.read_text().splitlines()]
    assert len(rows) == 6 and not any("error" in r for r in rows)
    assert all(r["privacy"]["planted_identifier_leaks"] == [] for r in rows)
    assert all(r["privacy"]["remote_payloads"] >= 1 for r in rows)
    report = score.score(rows, {c["id"]: c for c in SUITE["cases"]})
    assert set(report["arms"]) == {"a_only", "answer_verifier", "dual_lobe"}
    assert report["arms"]["dual_lobe"]["false_holds"] == 0
    score.export_adjudication(rows, {c["id"]: c for c in SUITE["cases"]}, tmp_path / "adj")
    assert (tmp_path / "adj" / "adjudication_sheet.csv").exists()
    sheet = (tmp_path / "adj" / "adjudication_sheet.csv").read_text()
    assert "dual_lobe" not in sheet and "answer_verifier" not in sheet  # blinded
