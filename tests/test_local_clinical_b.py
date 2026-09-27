import os

import pytest

from dual_lobe_crewai.llm_factory import primary_spec, resolve_role_specs


def test_clinical_b_defaults_to_loopback(monkeypatch):
    monkeypatch.delenv("DUAL_LOBE_CLINICAL_B_BASE_URL", raising=False)
    monkeypatch.delenv("DUAL_LOBE_B_CLINICAL_BASE_URL", raising=False)
    spec = primary_spec("B_CLINICAL")
    assert spec.base_url.startswith("http://127.")
    assert spec.model


def test_clinical_b_rejects_remote_endpoint(monkeypatch):
    monkeypatch.setenv("DUAL_LOBE_CLINICAL_B_BASE_URL", "https://api.example.com/v1")
    with pytest.raises(ValueError, match="local-only"):
        resolve_role_specs("B_CLINICAL")


def test_clinical_b_does_not_cross_role_failover(monkeypatch):
    monkeypatch.setenv("DUAL_LOBE_CROSS_ROLE_FAILOVER", "true")
    monkeypatch.setenv("DUAL_LOBE_CLINICAL_B_BASE_URL", "http://127.0.0.1:11434/v1")
    monkeypatch.setenv("DUAL_LOBE_A_MODEL", "openrouter/remote-a")
    monkeypatch.setenv("DUAL_LOBE_A_BASE_URL", "https://openrouter.ai/api/v1")
    specs = resolve_role_specs("B_CLINICAL")
    assert specs
    assert all(
        ("127.0.0.1" in (s.base_url or "") or "localhost" in (s.base_url or ""))
        for s in specs
    )
    assert all("remote-a" not in s.model for s in specs)


def test_clinical_b_rejects_remote_fallback(monkeypatch):
    monkeypatch.setenv("DUAL_LOBE_CLINICAL_B_BASE_URL", "http://127.0.0.1:11434/v1")
    monkeypatch.setenv(
        "DUAL_LOBE_B_CLINICAL_FALLBACKS",
        '[{"model":"openai/remote","base_url":"https://remote.example/v1"}]',
    )
    with pytest.raises(ValueError, match="local-only"):
        resolve_role_specs("B_CLINICAL")
