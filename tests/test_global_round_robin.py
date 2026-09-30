import asyncio
import json

from dual_lobe_crewai import runner
from dual_lobe_crewai.llm_factory import resolve_role_specs
from dual_lobe_crewai.provider_control import ProviderSpec

OR_MODEL = "openrouter/nvidia/nemotron-3-super-120b-a12b:free"
GROQ = "https://api.groq.com/openai/v1"


def _five_slot_pool(monkeypatch):
    for name in ("OPENAI_API_KEY", "OPENAI_API_BASE"):
        monkeypatch.delenv(name, raising=False)
    for role in ("A", "B"):
        monkeypatch.setenv(f"DUAL_LOBE_{role}_MODEL", "openai/openai/gpt-oss-120b")
        monkeypatch.setenv(f"DUAL_LOBE_{role}_BASE_URL", GROQ)
        monkeypatch.setenv(f"DUAL_LOBE_{role}_API_KEY", "groq-key")
    for i in (1, 2, 3):
        monkeypatch.setenv(f"OPENROUTER_API_KEY_{i}", f"or-{i}")
    monkeypatch.setenv("CHEAPAI_API_KEY", "cheap-key")
    rows = [{"model": OR_MODEL, "api_key_env": f"OPENROUTER_API_KEY_{i}", "label": f"openrouter-{i}"} for i in (1, 2, 3)]
    rows.append({"model": "openai/gemini-3-flash", "base_url": "https://cheapai.io/v1",
                 "api_key_env": "CHEAPAI_API_KEY", "label": "cheapai"})
    monkeypatch.setenv("DUAL_LOBE_FALLBACKS", json.dumps(rows))
    monkeypatch.setenv("DUAL_LOBE_CROSS_ROLE_FAILOVER", "false")


def test_each_slot_keeps_its_own_host_and_key(monkeypatch):
    _five_slot_pool(monkeypatch)
    for role in ("A", "B_VERIFY"):
        assert [(s.base_url, s.api_key) for s in resolve_role_specs(role)] == [
            (GROQ, "groq-key"),
            (None, "or-1"),
            (None, "or-2"),
            (None, "or-3"),
            ("https://cheapai.io/v1", "cheap-key"),
        ]


def test_rotation_is_one_global_cycle_across_lobes(monkeypatch):
    _five_slot_pool(monkeypatch)
    runner._rr_reset()
    roles = ["A", "B_VERIFY"] * 5
    starts = [runner._round_robin_specs(r, resolve_role_specs(r))[0].api_key for r in roles]
    assert starts == ["groq-key", "or-1", "or-2", "or-3", "cheap-key"] * 2


def test_provider_setup_failure_rotates_to_next(monkeypatch):
    runner._rr_reset()
    bad = ProviderSpec(model="bad/m", max_tokens=10, label="bad")
    good = ProviderSpec(model="good/m", max_tokens=10, label="good")

    def fake_make_llm(role, spec=None):
        if spec.model == "bad/m":
            raise ImportError("provider not installed")
        return spec

    async def fake_call(agent, d, e):
        return runner._current.model

    monkeypatch.setattr(runner, "make_llm", fake_make_llm)
    monkeypatch.setattr(runner, "_set_llm", lambda agent, llm: setattr(runner, "_current", llm))
    monkeypatch.setattr(runner, "_single_call", fake_call)
    out = asyncio.run(runner.run_one(object(), "x", "y", role_key="A", specs=[bad, good]))
    assert out == "good/m"
