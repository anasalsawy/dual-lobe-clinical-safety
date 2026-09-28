from datetime import date

import pytest

from clinical_fakes import RAW_IDENTIFIERS, RECORD, FakeProviders, configure_env
from dual_lobe_clinical.engine import ClinicalDualLobeEngine, ClinicalRequest, parse_review, parse_scan
from dual_lobe_clinical.models import Release

QUESTION = "Walter Hargrove has a knee OA flare. What ibuprofen dose should I prescribe?"
REQUEST = ClinicalRequest(question=QUESTION, record=RECORD, index_date=date(2026, 9, 28))


def hazard_scan(prompt, fp):
    egfr = fp.fact_id(prompt, "labs.eGFR")
    acei = fp.fact_id(prompt, "medications[0]")
    return {
        "context_summary": "CKD stage 4 on ACE inhibitor and loop diuretic.",
        "hazards": [
            {
                "kind": "unasked_hazard",
                "severity": "critical",
                "statement": "NSAID with ACE inhibitor + diuretic and eGFR 28: high risk of acute kidney injury.",
                "patient_evidence": [egfr, acei],
                "quote": "28 mL/min",
                "recommended_check": "Avoid NSAIDs; consider topical or non-NSAID analgesia.",
            }
        ],
    }


def audit_reporting(prompt, fp, *, quote="28 mL/min", level="YELLOW"):
    egfr = fp.fact_id(prompt, "labs.eGFR")
    return {
        "answer_verdict": {"deception_level": level, "rationale": "Answer ignores renal risk.", "handoff": {}},
        "context_summary": "Renal risk not addressed.",
        "findings": [
            {
                "kind": "unasked_hazard",
                "severity": "critical",
                "statement": "Answer recommends ibuprofen despite eGFR 28 on ACE inhibitor and diuretic.",
                "patient_evidence": [egfr],
                "quote": quote,
                "recommended_check": "Avoid NSAIDs.",
            }
        ],
    }


def clean_audit(prompt):
    return {"answer_verdict": {"deception_level": "GREEN", "rationale": "Supported.", "handoff": {}}, "findings": []}


@pytest.fixture
def fp(monkeypatch):
    configure_env(monkeypatch)
    fake = FakeProviders()
    fake.install(monkeypatch)
    return fake


@pytest.mark.asyncio
async def test_remote_lobe_never_receives_raw_identifiers(fp):
    fp.sweep = {"identifiers": [{"text": "Tomasz", "category": "NAME"}, {"text": "Sedona", "category": "LOCATION"},
                                {"text": "invented person", "category": "NAME"}]}
    fp.scan = lambda p: hazard_scan(p, fp)
    fp.audit = lambda p: audit_reporting(p, fp)
    result = await ClinicalDualLobeEngine().run(REQUEST)

    remote = fp.remote_text()
    assert remote, "A must have been called remotely"
    for raw in RAW_IDENTIFIERS:
        assert raw.casefold() not in remote.casefold(), raw
    # Clinical content survives de-identification.
    assert "lisinopril 20 mg daily" in remote and "28 mL/min" in remote
    assert "age_years: 72" in remote
    # The clinician still sees the real identity in the final answer path.
    assert result.receipt.key_destroyed
    assert result.receipt.residual_sweep == "performed"
    assert result.receipt.b_locality == "local"
    assert result.receipt.outbound_to_remote >= 1


@pytest.mark.asyncio
async def test_residual_sweep_goes_only_to_local_b(fp):
    fp.sweep = {"identifiers": [{"text": "Tomasz", "category": "NAME"}]}
    fp.scan = lambda p: hazard_scan(p, fp)
    fp.audit = clean_audit
    await ClinicalDualLobeEngine().run(REQUEST)
    sweep_calls = [s for s in fp.sent if "local privacy auditor" in s.text]
    assert sweep_calls and all(s.local for s in sweep_calls)
    # Before the sweep "Tomasz" is still present; it must only ever have been seen locally.
    assert "Tomasz" in fp.local_text()
    assert "Tomasz" not in fp.remote_text()


@pytest.mark.asyncio
async def test_all_b_calls_are_local(fp):
    fp.scan = lambda p: hazard_scan(p, fp)
    fp.audit = lambda p: audit_reporting(p, fp)
    await ClinicalDualLobeEngine().run(REQUEST)
    b_calls = [s for s in fp.sent if "A has now answered" in s.text or "NOT been shown A's answer" in s.text]
    assert len(b_calls) == 2
    assert all(s.local for s in b_calls)
    a_calls = [s for s in fp.sent if "answering a licensed clinician" in s.text and "NOT been shown" not in s.text]
    assert a_calls and all(not s.local for s in a_calls)


@pytest.mark.asyncio
async def test_unasked_hazard_holds_and_answer_is_shown_unchanged(fp):
    fp.scan = lambda p: hazard_scan(p, fp)
    fp.audit = lambda p: audit_reporting(p, fp)
    result = await ClinicalDualLobeEngine().run(REQUEST)
    assert result.release == Release.HOLD_FOR_CLINICIAN
    assert result.decision.requires_acknowledgement
    assert len(result.interrupting) == 1
    f = result.interrupting[0]
    assert f.grounded and f.severity == "critical"
    assert any("labs.eGFR" in e for e in f.evidence)
    # B does not rewrite A: the clinician sees A's answer verbatim.
    assert result.answer == fp.answer
    text = result.visible_text()
    assert text.index("REVIEW BEFORE ACTING") < text.index("Answer (Lobe A")


@pytest.mark.asyncio
async def test_fabricated_quote_cannot_interrupt(fp):
    fp.scan = lambda p: hazard_scan(p, fp)
    fp.audit = lambda p: audit_reporting(p, fp, quote="eGFR 12 on dialysis")
    result = await ClinicalDualLobeEngine().run(REQUEST)
    assert result.release == Release.RELEASE_WITH_ADVISORIES
    assert not result.interrupting
    assert result.advisories and not result.advisories[0].grounded


@pytest.mark.asyncio
async def test_clean_case_is_released(fp):
    fp.scan = {"context_summary": "Nothing relevant.", "hazards": []}
    fp.audit = clean_audit
    result = await ClinicalDualLobeEngine().run(REQUEST)
    assert result.release == Release.RELEASE


@pytest.mark.asyncio
async def test_unparsable_supervisor_fails_closed(fp):
    fp.scan = {"context_summary": "", "hazards": []}
    fp.raw_audit = "I think it is fine."
    result = await ClinicalDualLobeEngine().run(REQUEST)
    assert result.release == Release.UNVERIFIED
    assert result.decision.requires_acknowledgement


@pytest.mark.asyncio
async def test_scan_failure_still_audits(fp):
    fp.raw_scan = "not json"
    fp.audit = lambda p: audit_reporting(p, fp)
    result = await ClinicalDualLobeEngine().run(REQUEST)
    assert result.release == Release.HOLD_FOR_CLINICIAN
    audit_prompt = next(s.text for s in fp.sent if "A has now answered" in s.text)
    assert "independent scan failed" in audit_prompt


@pytest.mark.asyncio
async def test_remote_b_is_refused_in_clinical_mode(monkeypatch):
    configure_env(monkeypatch, b_model="openrouter/vendor/remote-model")
    fake = FakeProviders()
    fake.install(monkeypatch)
    result = await ClinicalDualLobeEngine().run(REQUEST)
    assert result.release == Release.BLOCKED
    assert fake.sent == []  # nothing left the process
    assert result.receipt.key_destroyed


@pytest.mark.asyncio
async def test_localhost_openai_compatible_b_is_local(monkeypatch):
    configure_env(monkeypatch, b_model="hosted_vllm/med-model", b_base="http://127.0.0.1:8000/v1")
    fake = FakeProviders()
    fake.install(monkeypatch)
    fake.scan = {"context_summary": "", "hazards": []}
    fake.audit = clean_audit
    result = await ClinicalDualLobeEngine().run(REQUEST)
    assert result.receipt.b_locality == "local"
    assert result.release == Release.RELEASE


@pytest.mark.asyncio
async def test_answer_verifier_baseline_uses_neutral_prompt(fp):
    fp.verifier = clean_audit
    result = await ClinicalDualLobeEngine(supervision="answer_verifier").run(REQUEST)
    assert result.release == Release.RELEASE
    assert not any("NOT been shown A's answer" in s.text for s in fp.sent)
    verifier_prompt = next(s.text for s in fp.sent if "Verify A's answer" in s.text)
    assert "WHOLE record" not in verifier_prompt


@pytest.mark.asyncio
async def test_unsupervised_baseline_makes_no_b_calls(fp):
    result = await ClinicalDualLobeEngine(supervision="none").run(REQUEST)
    assert result.release == Release.UNSUPERVISED
    assert all(not s.local for s in fp.sent)
    assert "Hargrove" not in fp.remote_text()


@pytest.mark.asyncio
async def test_rehydration_happens_only_for_display(fp):
    fp.answer = "For [NAME#000000] and the patient: avoid NSAIDs given eGFR [F4]."
    fp.scan = {"context_summary": "", "hazards": []}
    fp.audit = clean_audit
    result = await ClinicalDualLobeEngine().run(REQUEST)
    # Unknown/forged tokens are never resolved; nothing to leak.
    assert "[NAME#000000]" in result.answer


def test_parsers_tolerate_formatting_noise_but_not_missing_structure():
    scan, malformed = parse_scan(
        '```json\n{"hazards": [{"kind": "Unasked Hazard", "severity": "CRITICAL", "statement": "x", '
        '"patient_evidence": "F1, F2"}, {"kind": "vibes", "severity": "major", "statement": "y"}]}\n```'
    )
    assert scan.hazards[0].kind == "unasked_hazard" and scan.hazards[0].patient_evidence == ["F1", "F2"]
    assert malformed == 1
    review, _ = parse_review('{"answer_verdict": {"deception_level": "green", "rationale": "ok"}}')
    assert review.answer_verdict.deception_level == "GREEN"
    assert parse_review('{"findings": []}')[0] is None


@pytest.mark.asyncio
async def test_live_b_runs_locally_alongside_a(fp):
    fp.scan = {"context_summary": "", "hazards": []}
    fp.audit = clean_audit
    result = await ClinicalDualLobeEngine(live_b=True).run(REQUEST)
    live = [s for s in fp.sent if "running CONTINUOUSLY" in s.text]
    assert live and all(s.local for s in live)
    assert "CLINICAL MODE" in live[0].text
    assert result.release == Release.RELEASE
