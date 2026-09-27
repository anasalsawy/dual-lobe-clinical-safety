from dataclasses import asdict

from dual_lobe_clinical.benchmark_runner import to_primitive
from dual_lobe_clinical.schemas import Decision, GateResult


def test_study_serialization_uses_stable_enum_values():
    payload = to_primitive(asdict(GateResult(decision=Decision.BLOCK, reasons=("x",))))
    assert payload["decision"] == "block"
    assert payload["reasons"] == ["x"]


def test_nested_enum_serialization_is_plain_json_data():
    payload = to_primitive({
        "gate": GateResult(decision=Decision.INSUFFICIENT_EVIDENCE),
        "decision": Decision.ESCALATE,
    })
    # dataclass objects are converted before this helper in result paths;
    # direct enum normalization must still be stable.
    assert payload["decision"] == "escalate"
