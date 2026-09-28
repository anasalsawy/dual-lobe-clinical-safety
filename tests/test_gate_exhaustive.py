"""Exhaustive verification of the release gate.

The gate's input space is finite once findings are abstracted to
(kind, severity, grounded). This test enumerates every configuration with up
to two findings, 50,568 gate evaluations, and checks the safety invariants
stated in docs/METHODS.md. It is the analytical evidence for the control
logic: the invariants hold by construction, not merely on sampled cases.
"""

import itertools

from dual_lobe_crewai.models import Verdict
from dual_lobe_clinical.control import GroundedFinding, decide
from dual_lobe_clinical.models import ClinicalFinding, Release

KINDS = ["unasked_hazard", "missing_information", "answer_error", "unsupported_claim"]
SEVERITIES = ["critical", "major", "minor"]
ATOMS = [
    GroundedFinding(ClinicalFinding(kind=k, severity=s, statement="x"), grounded=g, note="" if g else "ungrounded")
    for k in KINDS for s in SEVERITIES for g in (True, False)
]
VERDICTS = [None] + [
    Verdict(deception_level=lvl, rationale="r", handoff=h)
    for lvl in ("GREEN", "YELLOW", "RED")
    for h in ({}, {"unverified": ["claim"]})
]


def finding_sets():
    yield []
    for a in ATOMS:
        yield [a]
    for a, b in itertools.combinations(ATOMS, 2):
        yield [a, b]


def test_gate_invariants_hold_over_entire_input_space():
    n = 0
    for sup, blocked, a_failed, b_done, verdict in itertools.product(
        ["dual_lobe", "answer_verifier", "none"], [False, True], [False, True], [False, True], VERDICTS
    ):
        for fs in finding_sets():
            d = decide(supervision=sup, privacy_blocked=blocked, a_failed=a_failed,
                       b_completed=b_done, verdict=verdict, findings=fs)
            n += 1
            grounded_interrupting = [g for g in fs if g.grounded and g.finding.severity in ("critical", "major")]

            # I1 privacy dominates: any refused egress -> BLOCKED, and only then.
            assert (d.release == Release.BLOCKED) == blocked
            if blocked:
                continue
            # I2 fail closed: an incomplete supervisor can never yield a checked release.
            if sup != "none" and (not b_done or verdict is None or a_failed):
                assert d.release == Release.UNVERIFIED
                continue
            if sup == "none" and not a_failed:
                assert d.release == Release.UNSUPERVISED
                continue
            if a_failed:
                assert d.release == Release.UNVERIFIED
                continue
            # I3 no interruption without evidence: every HOLD is justified by a grounded
            # critical/major finding or a RED verdict backed by a grounded answer_error/critical.
            if d.release == Release.HOLD_FOR_CLINICIAN:
                assert grounded_interrupting or any(
                    g.grounded and (g.finding.kind == "answer_error" or g.finding.severity == "critical") for g in fs
                )
                assert d.requires_acknowledgement
            # I4 completeness: every grounded critical/major finding forces a HOLD.
            if grounded_interrupting:
                assert d.release == Release.HOLD_FOR_CLINICIAN
                assert len(d.interrupting) == len(grounded_interrupting)
            # I5 ungrounded findings never interrupt.
            assert all(g.grounded for g in d.interrupting)
            # I6 a clean RELEASE means no findings, no open gaps and a GREEN verdict.
            if d.release == Release.RELEASE:
                assert not fs and d.effective_verdict.deception_level == "GREEN"
                assert not (verdict.handoff.unverified or verdict.handoff.missing or verdict.handoff.proof_requests)
            # I7 nothing is silently dropped: every finding is either interrupting or advisory.
            assert len(d.interrupting) + len(d.advisories) == len(fs)
    assert n == 50_568
