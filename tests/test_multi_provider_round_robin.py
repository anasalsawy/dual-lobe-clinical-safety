import asyncio

from dual_lobe_crewai import runner


class Spec:
    def __init__(self, label):
        self.label = label


def test_round_robin_is_global_across_roles():
    runner._rr_reset()
    specs = [Spec("p1"), Spec("p2"), Spec("p3")]

    assert [x.label for x in runner._round_robin_specs("A", specs)] == ["p1", "p2", "p3"]
    assert [x.label for x in runner._round_robin_specs("B_VERIFY", specs)] == ["p2", "p3", "p1"]
    assert [x.label for x in runner._round_robin_specs("A", specs)] == ["p3", "p1", "p2"]
    assert [x.label for x in runner._round_robin_specs("A_CHILD", specs)] == ["p1", "p2", "p3"]


def test_round_robin_single_provider_is_unchanged():
    runner._rr_reset()
    specs = [Spec("only")]
    assert [x.label for x in runner._round_robin_specs("A", specs)] == ["only"]


def test_round_robin_four_provider_sequence_mixed_roles():
    runner._rr_reset()
    specs = [Spec("1"), Spec("2"), Spec("3"), Spec("4")]
    roles = ["A", "B_VERIFY", "A", "B_VERIFY", "A_MERGE", "B_WORKER", "A", "B_VERIFY"]
    starts = [runner._round_robin_specs(r, specs)[0].label for r in roles]
    assert starts == ["1", "2", "3", "4", "1", "2", "3", "4"]


def test_role_missing_next_provider_starts_on_next_it_has():
    runner._rr_reset()
    p1, p2, p3 = Spec("p1"), Spec("p2"), Spec("p3")
    runner._round_robin_specs("A", [p1, p2, p3])
    # Cycle is now at p2; B only has p1 and p3, so it starts on p3.
    assert runner._round_robin_specs("B_VERIFY", [p1, p3])[0].label == "p3"
    assert runner._round_robin_specs("A", [p1, p2, p3])[0].label == "p1"


def test_provider_setup_failure_rotates_to_next(monkeypatch):
    runner._rr_reset()
    from dual_lobe_crewai.provider_control import ProviderSpec

    bad = ProviderSpec(model="bad/m", max_tokens=10, label="bad")
    good = ProviderSpec(model="good/m", max_tokens=10, label="good")
    monkeypatch.setattr(runner, "resolve_role_specs", lambda role: [bad, good])

    class L:
        def __init__(self, model):
            self.model = model

    def fake_make_llm(role, spec=None, extra_body=None):
        if spec.model == "bad/m":
            raise ImportError("provider not installed")
        return L(spec.model)

    async def fake_call(agent, d, e):
        return agent.llm.model

    monkeypatch.setattr(runner, "make_llm", fake_make_llm)
    monkeypatch.setattr(runner, "_single_call", fake_call)

    class Agent:
        role = "planner"
        llm = None

    out = asyncio.run(runner.run_one(Agent(), "x", "y", role_key="A", persistent_state=False))
    assert out == "good/m"
