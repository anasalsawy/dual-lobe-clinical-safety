from __future__ import annotations

import json
import os
from dataclasses import replace
from urllib.parse import urlparse
from crewai import LLM

from .provider_control import ProviderSpec


def _role_defaults(role: str) -> tuple[str, int, str]:
    role = role.upper()
    a_default = os.getenv("DUAL_LOBE_A_MODEL", "openrouter/nvidia/nemotron-3-super-120b-a12b:free")
    b_default = os.getenv("DUAL_LOBE_B_MODEL", a_default)
    if role == "A":
        return a_default, int(os.getenv("DUAL_LOBE_A_MAX_TOKENS", "8000")), "A"
    if role == "A_CHILD":
        return os.getenv("DUAL_LOBE_CHILD_MODEL", a_default), int(os.getenv("DUAL_LOBE_CHILD_MAX_TOKENS", "6000")), "A"
    if role == "A_MERGE":
        return os.getenv("DUAL_LOBE_A_MERGE_MODEL", a_default), int(os.getenv("DUAL_LOBE_A_MERGE_MAX_TOKENS", "12000")), "A"
    if role == "B_VERIFY":
        return os.getenv("DUAL_LOBE_B_VERIFY_MODEL", b_default), int(os.getenv("DUAL_LOBE_B_VERIFY_MAX_TOKENS", "6000")), "B"
    if role == "B_WORKER":
        return os.getenv("DUAL_LOBE_B_WORKER_MODEL", b_default), int(os.getenv("DUAL_LOBE_B_WORKER_MAX_TOKENS", "6000")), "B"
    if role == "B_CLINICAL":
        return (
            os.getenv("DUAL_LOBE_CLINICAL_B_MODEL", "openai/clinical-b-guardian"),
            int(os.getenv("DUAL_LOBE_CLINICAL_B_MAX_TOKENS", "6000")),
            "CLINICAL_B",
        )
    raise ValueError(f"Unknown LLM role: {role}")


def primary_spec(role: str) -> ProviderSpec:
    role = role.upper()
    model, max_tokens, key_role = _role_defaults(role)
    if role == "B_CLINICAL":
        api_key = (
            os.getenv("DUAL_LOBE_CLINICAL_B_API_KEY")
            or os.getenv("DUAL_LOBE_B_CLINICAL_API_KEY")
            or "local"
        )
        base_url = (
            os.getenv("DUAL_LOBE_CLINICAL_B_BASE_URL")
            or os.getenv("DUAL_LOBE_B_CLINICAL_BASE_URL")
            or "http://127.0.0.1:11434/v1"
        )
    else:
        api_key = os.getenv(f"DUAL_LOBE_{role}_API_KEY") or os.getenv(f"DUAL_LOBE_{key_role}_API_KEY") or os.getenv("OPENAI_API_KEY")
        base_url = os.getenv(f"DUAL_LOBE_{role}_BASE_URL") or os.getenv(f"DUAL_LOBE_{key_role}_BASE_URL") or os.getenv("OPENAI_API_BASE")
    tier = (os.getenv(f"DUAL_LOBE_{role}_TIER") or os.getenv(f"DUAL_LOBE_{key_role}_TIER") or os.getenv("DUAL_LOBE_PROVIDER_TIER", "auto")).lower()
    rpm = _opt_int(os.getenv(f"DUAL_LOBE_{role}_RPM") or os.getenv(f"DUAL_LOBE_{key_role}_RPM"))
    tpm = _opt_int(os.getenv(f"DUAL_LOBE_{role}_TPM") or os.getenv(f"DUAL_LOBE_{key_role}_TPM"))
    return ProviderSpec(model=model, max_tokens=max_tokens, api_key=api_key, base_url=base_url, tier=tier, rpm=rpm, tpm=tpm, label=f"{role}:primary")


def _opt_int(v):
    try:
        return int(v) if v not in (None, "") else None
    except Exception:
        return None


def _fallback_json(role: str) -> list[dict]:
    raw = os.getenv(f"DUAL_LOBE_{role.upper()}_FALLBACKS") or os.getenv("DUAL_LOBE_FALLBACKS") or "[]"
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _is_local_base_url(base_url: str | None) -> bool:
    if not base_url:
        return False
    try:
        parsed = urlparse(base_url)
        host = (parsed.hostname or "").lower()
    except Exception:
        return False
    return (
        host == "localhost"
        or host == "::1"
        or host == "host.docker.internal"
        or host.startswith("127.")
    )


def _assert_clinical_b_local(spec: ProviderSpec) -> None:
    testing_mode = os.getenv("DUAL_LOBE_TESTING_MODE", "false").lower() in {"1", "true", "yes", "on"}
    local_only = os.getenv("DUAL_LOBE_CLINICAL_B_LOCAL_ONLY", "true").lower() in {"1", "true", "yes", "on"}
    if testing_mode and not local_only:
        return
    if not _is_local_base_url(spec.base_url):
        raise ValueError(
            "B_CLINICAL is local-only unless testing mode is explicitly enabled with "
            "DUAL_LOBE_TESTING_MODE=true and DUAL_LOBE_CLINICAL_B_LOCAL_ONLY=false."
        )


def resolve_role_specs(role: str) -> list[ProviderSpec]:
    role = role.upper()
    primary = primary_spec(role)
    if role == "B_CLINICAL":
        _assert_clinical_b_local(primary)
    out = [primary]
    for i, row in enumerate(_fallback_json(role), 1):
        if not isinstance(row, dict) or not row.get("model"):
            continue
        key = row.get("api_key")
        if not key and row.get("api_key_env"):
            key = os.getenv(str(row["api_key_env"]))
        candidate = ProviderSpec(
            model=str(row["model"]),
            max_tokens=int(row.get("max_tokens") or primary.max_tokens),
            api_key=key or primary.api_key,
            base_url=row.get("base_url") or primary.base_url,
            tier=str(row.get("tier") or "auto").lower(),
            rpm=_opt_int(row.get("rpm")),
            tpm=_opt_int(row.get("tpm")),
            label=str(row.get("label") or f"{role}:fallback:{i}"),
        )
        if role == "B_CLINICAL":
            _assert_clinical_b_local(candidate)
        out.append(candidate)

    if role != "B_CLINICAL" and os.getenv("DUAL_LOBE_CROSS_ROLE_FAILOVER", "true").lower() in {"1", "true", "yes", "on"}:
        for other in ["A", "A_CHILD", "B_VERIFY"]:
            if other == role or (role == "A_MERGE" and other == "A"):
                continue
            alt = primary_spec(other)
            alt = replace(alt, max_tokens=primary.max_tokens, label=f"{role}:cross:{other}")
            out.append(alt)

    dedup, seen = [], set()
    for s in out:
        k = (s.model, s.base_url, s.api_key)
        if k not in seen:
            dedup.append(s)
            seen.add(k)
    return dedup


def make_llm(
    role: str,
    spec: ProviderSpec | None = None,
    *,
    extra_body: dict | None = None,
) -> LLM:
    spec = spec or primary_spec(role)
    kwargs = {"model": spec.model, "max_tokens": spec.max_tokens}
    if extra_body:
        kwargs["extra_body"] = dict(extra_body)
    if spec.api_key:
        kwargs["api_key"] = spec.api_key
    if spec.base_url:
        kwargs["base_url"] = spec.base_url
    return LLM(**kwargs)
