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
    assert len(ids) == len(set(ids)) == 133
    types = {c["type"] for c in SUITE["cases"]}
    assert types == {"unasked_hazard", "missing_information", "negative_control"}
    by_id = {c["id"]: c for c in SUITE["cases"]}
    for c in SUITE["cases"]:
        assert c["phi"], c["id"]
        assert c["gold"].get("basis"), c["id"]  # provenance for every label
        if c.get("twin_of"):
            base = by_id[c["twin_of"]]
            assert base["type"] == "unasked_hazard" and c["type"] == "negative_control"
            assert c["question"] == base["question"]  # only the record differs
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
    assert len({r["provenance"]["cases_sha256"] for r in rows}) == 1
    assert rows[0]["provenance"]["a_model"].startswith("openrouter/")
    report = score.score(rows, {c["id"]: c for c in SUITE["cases"]})
    assert set(report["arms"]) == {"a_only", "answer_verifier", "dual_lobe"}
    assert report["arms"]["dual_lobe"]["false_holds"] == 0
    score.export_adjudication(rows, {c["id"]: c for c in SUITE["cases"]}, tmp_path / "adj")
    assert (tmp_path / "adj" / "adjudication_sheet.csv").exists()
    sheet = (tmp_path / "adj" / "adjudication_sheet.csv").read_text()
    assert "dual_lobe" not in sheet and "answer_verifier" not in sheet  # blinded

    # Resume: drop the last row (as if the run was cut off) and append only it.
    lines = out.read_text().splitlines()
    out.write_text("\n".join(lines[:-1]) + "\n")
    args.resume = str(out)
    assert await run_study.run(args) == out
    resumed = [json.loads(x) for x in out.read_text().splitlines()]
    assert len(resumed) == 6
    assert {(r["case_id"], r["arm"]) for r in resumed} == {(r["case_id"], r["arm"]) for r in rows}


def test_repeat_consistency_and_per_case_tally():
    cases = {c["id"]: c for c in SUITE["cases"]}
    def row(cid, rep, answer, release="RELEASE"):
        return {"case_id": cid, "case_type": cases[cid]["type"], "arm": "dual_lobe", "repeat": rep,
                "release": release, "answer_deidentified": answer, "findings": [], "fact_paths": {},
                "privacy": {"planted_identifier_leaks": []}, "logical_model_calls": 3, "timings_ms": {"total_ms": 1}}
    rows = [row("H01", 0, "renal risk"), row("H01", 1, "fine"), row("H02", 0, "statin"), row("H02", 1, "statin"),
            row("N01", 0, "ok"), row("N01", 1, "ok", "HOLD_FOR_CLINICIAN")]
    arm = score.score(rows, cases)["arms"]["dual_lobe"]
    assert arm["per_case"]["H01"] == "1/2" and arm["per_case"]["H02"] == "2/2"
    assert arm["repeat_consistency"] == pytest.approx(1 / 3)
    assert arm["false_holds"] == 1


def test_adjudication_kappa_consensus_and_tiebreak(tmp_path):
    import adjudication

    assert adjudication.cohen_kappa([(True, True), (False, False)]) == 1.0
    assert adjudication.cohen_kappa([(True, False), (False, True)]) == pytest.approx(-1.0)
    head = "item,case_id,question,what_the_clinician_sees,gold_issue_surfaced(Y/N),false_alarm(Y/N),harmful_if_followed(Y/N),notes\n"
    (tmp_path / "r1.csv").write_text(head + "1,H01,q,s,Y,N,N,\n2,H01,q,s,N,N,Y,\n3,N01,q,s,,Y,N,\n")
    (tmp_path / "r2.csv").write_text(head + "1,H01,q,s,Y,N,N,\n2,H01,q,s,Y,N,Y,\n3,N01,q,s,,Y,N,\n")
    (tmp_path / "r3.csv").write_text(head + "2,H01,q,s,N,,,\n")
    key = [{"item": 1, "arm": "dual_lobe"}, {"item": 2, "arm": "a_only"}, {"item": 3, "arm": "dual_lobe"}]
    cases = {c["id"]: c for c in SUITE["cases"]}
    r1, r2 = adjudication.read_sheet(tmp_path / "r1.csv"), adjudication.read_sheet(tmp_path / "r2.csv")
    out = adjudication.analyse(key, r1, r2, None, cases)
    assert out["unresolved_disagreements"] == [{"item": 2, "case_id": "H01", "field": "surfaced"}]
    out = adjudication.analyse(key, r1, r2, adjudication.read_sheet(tmp_path / "r3.csv"), cases)
    assert not out["unresolved_disagreements"]
    assert out["adjudicated"]["dual_lobe"]["surfaced"]["k"] == 1
    assert out["adjudicated"]["a_only"]["surfaced"]["k"] == 0
    assert out["adjudicated"]["dual_lobe"]["false_alarm"]["k"] == 1


def test_matched_pair_discrimination():
    cases = {c["id"]: c for c in SUITE["cases"]}
    def row(cid, release):
        return {"case_id": cid, "case_type": cases[cid]["type"], "arm": "dual_lobe", "repeat": 0, "release": release,
                "answer_deidentified": "", "findings": [], "fact_paths": {}, "privacy": {"planted_identifier_leaks": []},
                "logical_model_calls": 3, "timings_ms": {"total_ms": 1}}
    rows = [row("H01", "HOLD_FOR_CLINICIAN"), row("T01", "RELEASE"),
            row("H03", "HOLD_FOR_CLINICIAN"), row("T03", "HOLD_FOR_CLINICIAN")]
    mp = score.score(rows, cases)["arms"]["dual_lobe"]["matched_pairs"]
    assert mp["n"] == 2 and mp["hold_hazard_only"] == 1 and mp["hold_both"] == 1
    assert mp["discrimination"] == 0.5


def test_label_validation_export_and_summary(tmp_path):
    import csv as _csv
    import export_label_validation as elv

    out = tmp_path / "v.csv"
    assert elv.export(str(CASES), str(out)) == 133
    text = out.read_text()
    assert "Hargrove" not in text  # validators see the de-identified record
    rows = list(_csv.DictReader(out.open()))
    a, b = tmp_path / "a.csv", tmp_path / "b.csv"
    for path, mark in ((a, "CONFIRM"), (b, "CORRECT")):
        with path.open("w", newline="") as fh:
            w = _csv.DictWriter(fh, fieldnames=rows[0].keys())
            w.writeheader()
            for r in rows[:3]:
                w.writerow({**r, "CONFIRM_or_CORRECT": "CONFIRM" if r["case_id"] != "H02" else mark})
    s = elv.summarize([str(a), str(b)])
    assert s["confirmed_by_all"] == 2 and s["disputed"][0]["case_id"] == "H02"
