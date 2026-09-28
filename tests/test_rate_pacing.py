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
