from dual_lobe_clinical.engine import ClinicalDualLobeEngine
from dual_lobe_clinical.schemas import Decision, GateResult


def gate(decision):
    return GateResult(decision=decision)


def test_release_only_pass_and_warn():
    candidate = "candidate"
    assert ClinicalDualLobeEngine._release(candidate, gate(Decision.PASS)) == candidate
    assert ClinicalDualLobeEngine._release(candidate, gate(Decision.WARN)) == candidate
    for decision in (
        Decision.REVISE,
        Decision.BLOCK,
        Decision.ESCALATE,
        Decision.INSUFFICIENT_EVIDENCE,
    ):
        assert ClinicalDualLobeEngine._release(candidate, gate(decision)) is None
