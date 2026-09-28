import asyncio

from dual_lobe_crewai.provider_control import AdaptiveRateController, ProviderSpec


def spec(rpm=None):
    return ProviderSpec(
        model="test/model",
        max_tokens=1000,
        api_key="x",
        base_url="https://example.test/v1",
        rpm=rpm,
    )


def test_global_max_rpm_is_used_when_role_limit_missing(monkeypatch):
    monkeypatch.setenv("DUAL_LOBE_MAX_RPM", "30")
    monkeypatch.setenv("DUAL_LOBE_RATE_SAFETY", "1.0")
    ctl = AdaptiveRateController()
    rpm, tpm = ctl.limits(spec())
    assert rpm == 30
    assert tpm is None


def test_explicit_role_rpm_beats_global_limit(monkeypatch):
    monkeypatch.setenv("DUAL_LOBE_MAX_RPM", "30")
    monkeypatch.setenv("DUAL_LOBE_RATE_SAFETY", "1.0")
    ctl = AdaptiveRateController()
    rpm, _ = ctl.limits(spec(rpm=12))
    assert rpm == 12


def test_safety_margin_reduces_effective_rpm(monkeypatch):
    monkeypatch.setenv("DUAL_LOBE_RATE_SAFETY", "0.9")
    ctl = AdaptiveRateController()
    rpm, _ = ctl.limits(spec(rpm=20))
    assert rpm == 18


def test_rpm_pacer_reserves_next_slot(monkeypatch):
    monkeypatch.setenv("DUAL_LOBE_RATE_SAFETY", "1.0")
    ctl = AdaptiveRateController()
    s = spec(rpm=60)

    asyncio.run(ctl.acquire(s, 1))
    assert ctl._next_request_at[s.key] > 0


def test_second_request_is_delayed_by_even_pacing(monkeypatch):
    monkeypatch.setenv("DUAL_LOBE_RATE_SAFETY", "1.0")
    ctl = AdaptiveRateController()
    s = spec(rpm=6000)  # 10 ms spacing keeps test fast.

    async def run_two():
        loop = asyncio.get_running_loop()
        t0 = loop.time()
        await ctl.acquire(s, 1)
        await ctl.acquire(s, 1)
        return loop.time() - t0

    elapsed = asyncio.run(run_two())
    assert elapsed >= 0.008


def test_openrouter_free_rpm_is_detected_automatically(monkeypatch):
    monkeypatch.delenv("DUAL_LOBE_MAX_RPM", raising=False)
    monkeypatch.setenv("DUAL_LOBE_RATE_SAFETY", "1.0")
    ctl = AdaptiveRateController()
    s = ProviderSpec(
        model="openrouter/nvidia/nemotron-3-super-120b-a12b:free",
        max_tokens=1000,
        api_key="x",
        base_url="https://openrouter.ai/api/v1",
        tier="auto",
    )
    rpm, _ = ctl.limits(s)
    assert rpm == 20
    assert ctl.limit_source(s, "RPM") == "provider_tier_auto"


def test_groq_free_rpm_is_detected_from_provider_and_tier(monkeypatch):
    monkeypatch.delenv("DUAL_LOBE_MAX_RPM", raising=False)
    monkeypatch.setenv("DUAL_LOBE_RATE_SAFETY", "1.0")
    ctl = AdaptiveRateController()
    s = ProviderSpec(
        model="groq/openai/gpt-oss-20b",
        max_tokens=1000,
        api_key="x",
        base_url="https://api.groq.com/openai/v1",
        tier="free",
    )
    rpm, _ = ctl.limits(s)
    assert rpm == 30
    assert ctl.limit_source(s, "RPM") == "provider_tier_auto"


def test_groq_request_limit_header_is_not_misread_as_rpm(monkeypatch):
    monkeypatch.setenv("DUAL_LOBE_RATE_SAFETY", "1.0")
    ctl = AdaptiveRateController()
    s = ProviderSpec(
        model="groq/openai/gpt-oss-20b",
        max_tokens=1000,
        api_key="x",
        base_url="https://api.groq.com/openai/v1",
        tier="free",
    )

    class Response:
        headers = {"x-ratelimit-limit-requests": "14400"}

    class Error(Exception):
        response = Response()

    learned = ctl.learn_from_error(s, Error("temporary failure"))
    assert learned.rpm is None
    rpm, _ = ctl.limits(s)
    assert rpm == 30


def test_official_web_discovery_overrides_preset(monkeypatch):
    monkeypatch.setenv("DUAL_LOBE_RATE_SAFETY", "1.0")
    ctl = AdaptiveRateController()
    s = ProviderSpec(
        model="openrouter/example:free",
        max_tokens=1000,
        api_key="x",
        base_url="https://openrouter.ai/api/v1",
        tier="free",
    )

    monkeypatch.setattr(
        ctl,
        "_fetch_text",
        lambda url: "Free tier limits: 7 requests per minute (RPM) and 10000 tokens per minute (TPM).",
    )
    asyncio.run(ctl.ensure_discovered(s))
    rpm, tpm = ctl.limits(s)
    assert rpm == 7
    assert tpm == 10000
    assert ctl.limit_source(s, "RPM") == "official_web"


def test_web_discovery_is_cached(monkeypatch):
    monkeypatch.setenv("DUAL_LOBE_RATE_SAFETY", "1.0")
    ctl = AdaptiveRateController()
    ctl.discovery_ttl_s = 3600
    s = ProviderSpec(
        model="openrouter/example:free",
        max_tokens=1000,
        api_key="x",
        base_url="https://openrouter.ai/api/v1",
        tier="free",
    )
    calls = {"n": 0}

    def fake_fetch(url):
        calls["n"] += 1
        return "20 requests per minute"

    monkeypatch.setattr(ctl, "_fetch_text", fake_fetch)
    asyncio.run(ctl.ensure_discovered(s))
    first_pass_calls = calls["n"]
    assert first_pass_calls >= 1
    asyncio.run(ctl.ensure_discovered(s))
    assert calls["n"] == first_pass_calls


def test_web_discovery_failure_falls_back_to_preset(monkeypatch):
    monkeypatch.setenv("DUAL_LOBE_RATE_SAFETY", "1.0")
    ctl = AdaptiveRateController()
    s = ProviderSpec(
        model="openrouter/example:free",
        max_tokens=1000,
        api_key="x",
        base_url="https://openrouter.ai/api/v1",
        tier="free",
    )

    def boom(url):
        raise OSError("offline")

    monkeypatch.setattr(ctl, "_fetch_text", boom)
    asyncio.run(ctl.ensure_discovered(s))
    rpm, _ = ctl.limits(s)
    assert rpm == 20
    assert ctl.limit_source(s, "RPM") == "provider_tier_auto"
