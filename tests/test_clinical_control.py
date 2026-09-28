"""The release gate and grounding rules, one test per rule (see docs/METHODS.md)."""

from dual_lobe_crewai.models import Verdict
from dual_lobe_clinical.control import decide, effective_verdict, ground_all, ground_finding
from dual_lobe_clinical.models import ClinicalFinding, Release

FACTS = {"F1": "age_years: 71", "F2": "medications[0]: lisinopril 20 mg daily", "F3": "labs.eGFR: 28 mL/min"}
CTX = dict(facts=FACTS, question="What ibuprofen dose?", answer="Ibuprofen 400 mg TID [F1].", knowledge_ids={"K1"})


def f(kind="unasked_hazard", severity="critical", evidence=("F3",), quote="", knowledge=()):
    return ClinicalFinding(kind=kind, severity=severity, statement="s", patient_evidence=list(evidence),
                           quote=quote, knowledge_evidence=list(knowledge))


def v(level="YELLOW", **handoff):
    return Verdict(deception_level=level, rationale="r", handoff=handoff)


# -- grounding ---------------------------------------------------------------

def test_grounded_hazard_with_real_quote():
    assert ground_finding(f(quote="28 ML/MIN"), **CTX).grounded


def test_nonexistent_fact_is_ungrounded():
    g = ground_finding(f(evidence=("F9",)), **CTX)
    assert not g.grounded and "does not exist" in g.note


def test_fabricated_quote_is_ungrounded():
    assert not ground_finding(f(quote="eGFR 12"), **CTX).grounded


def test_unretrieved_knowledge_citation_is_ungrounded():
    assert ground_finding(f(knowledge=("K1",)), **CTX).grounded
    assert not ground_finding(f(knowledge=("K7",)), **CTX).grounded


def test_hazard_must_cite_a_patient_fact():
    assert not ground_finding(f(evidence=("Q",)), **CTX).grounded


def test_missing_information_may_cite_the_question():
    assert ground_finding(f(kind="missing_information", evidence=("Q",)), **CTX).grounded


def test_unsupported_claim_must_cite_the_answer():
    assert not ground_finding(f(kind="unsupported_claim", evidence=("F1",)), **CTX).grounded
    assert ground_finding(f(kind="unsupported_claim", evidence=("A",), quote="400 mg TID"), **CTX).grounded


def test_reference_spellings_are_normalized():
    assert ground_finding(f(evidence=("[f3]",)), **CTX).grounded
    assert ground_finding(f(evidence=("F-3",)), **CTX).grounded


def test_duplicates_keep_most_severe_and_grounded_critical_first():
    items = [f(severity="minor"), f(evidence=("F9",)), f(), f()]
    out = ground_all(items, **CTX)
    assert len(out) == 2
    assert out[0].grounded and out[0].finding.severity == "critical"
    assert not out[-1].grounded


# -- verdict rules -------------------------------------------------------------

def test_green_impossible_with_grounded_finding():
    verdict, _ = effective_verdict(v("GREEN"), ground_all([f(severity="minor")], **CTX))
    assert verdict.deception_level == "YELLOW"


def test_green_impossible_with_open_handoff_gap():
    verdict, _ = effective_verdict(v("GREEN", unverified=["dose"]), [])
    assert verdict.deception_level == "YELLOW"


def test_red_without_evidence_is_downgraded():
    verdict, notes = effective_verdict(v("RED"), ground_all([f(evidence=("F9",))], **CTX))
    assert verdict.deception_level == "YELLOW" and notes


def test_red_with_grounded_answer_error_stands():
    verdict, _ = effective_verdict(v("RED"), ground_all([f(kind="answer_error", severity="major")], **CTX))
    assert verdict.deception_level == "RED"


# -- gate, in rule order -------------------------------------------------------

def gate(**kw):
    base = dict(supervision="dual_lobe", privacy_blocked=False, a_failed=False, b_completed=True,
                verdict=v("GREEN"), findings=[])
    base.update(kw)
    return decide(**base)


def test_rule1_privacy_block_wins_over_everything():
    assert gate(privacy_blocked=True, a_failed=True, b_completed=False).release == Release.BLOCKED


def test_rule2_primary_failure_is_unverified():
    assert gate(a_failed=True).release == Release.UNVERIFIED


def test_rule3_no_supervision_is_labelled_unsupervised():
    assert gate(supervision="none", verdict=None, b_completed=False).release == Release.UNSUPERVISED


def test_rule4_supervisor_failure_fails_closed():
    d = gate(b_completed=False, verdict=None)
    assert d.release == Release.UNVERIFIED and d.requires_acknowledgement


def test_rule5_grounded_major_holds():
    d = gate(verdict=v("YELLOW"), findings=ground_all([f(severity="major")], **CTX))
    assert d.release == Release.HOLD_FOR_CLINICIAN and d.requires_acknowledgement
    assert len(d.interrupting) == 1


def test_rule5_ungrounded_critical_does_not_hold():
    d = gate(verdict=v("YELLOW"), findings=ground_all([f(quote="invented")], **CTX))
    assert d.release == Release.RELEASE_WITH_ADVISORIES
    assert not d.interrupting and len(d.advisories) == 1


def test_rule5_grounded_red_holds():
    d = gate(verdict=v("RED"), findings=ground_all([f(kind="answer_error", severity="minor")], **CTX))
    assert d.release == Release.HOLD_FOR_CLINICIAN


def test_rule6_minor_only_is_advisory():
    d = gate(verdict=v("YELLOW"), findings=ground_all([f(severity="minor")], **CTX))
    assert d.release == Release.RELEASE_WITH_ADVISORIES and not d.requires_acknowledgement


def test_rule6_yellow_without_findings_is_advisory():
    assert gate(verdict=v("YELLOW")).release == Release.RELEASE_WITH_ADVISORIES


def test_rule7_clean_release():
    d = gate()
    assert d.release == Release.RELEASE and not d.interrupting and not d.advisories
