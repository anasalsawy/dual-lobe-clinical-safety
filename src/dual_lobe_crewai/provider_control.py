from __future__ import annotations

import asyncio
import os
import re
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, replace
from typing import Any


@dataclass(frozen=True)
class ProviderSpec:
    model: str
    max_tokens: int
    api_key: str | None = None
    base_url: str | None = None
    tier: str = "auto"  # auto | free | paid
    rpm: int | None = None
    tpm: int | None = None
    label: str = ""

    @property
    def provider(self) -> str:
        base = (self.base_url or "").lower()
        model = self.model.lower()
        if "groq.com" in base or "groq/" in model or model.startswith("hosted_vllm/openai/"):
            return "groq"
        if "openrouter.ai" in base or model.startswith("openrouter/"):
            return "openrouter"
        if "cerebras" in base or model.startswith("cerebras/"):
            return "cerebras"
        if "deepinfra" in base or model.startswith("deepinfra/"):
            return "deepinfra"
        return (base.split("//")[-1].split("/")[0] if base else model.split("/")[0] or "unknown").replace(".", "_")

    @property
    def effective_tier(self) -> str:
        if self.tier in {"free", "paid"}:
            return self.tier
        if ":free" in self.model.lower():
            return "free"
        return "auto"

    @property
    def key(self) -> str:
        return f"{self.provider}|{self.base_url or ''}|{self.model}"


@dataclass
class LearnedLimit:
    rpm: int | None = None
    tpm: int | None = None
    retry_after_s: float | None = None
    learned_at: float = 0.0


class AdaptiveRateController:
    """Provider/model-aware local pacer.

    Design goals:
    - Paid/unknown tiers are not artificially slowed when no real limit is known.
    - Free-tier hints can be supplied explicitly via env.
    - Exact limits are learned from rate-limit response headers/error messages.
    - Each provider/model has an independent rolling RPM/TPM bucket.
    - A learned limit only throttles the provider/model that exposed it.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._tokens: dict[str, deque[tuple[float, int]]] = defaultdict(deque)
        self._learned: dict[str, LearnedLimit] = defaultdict(LearnedLimit)
        self._next_request_at: dict[str, float] = defaultdict(float)
        self.safety = float(os.getenv("DUAL_LOBE_RATE_SAFETY", "0.92"))

    def _env_free_hint(self, spec: ProviderSpec, kind: str) -> int | None:
        if spec.effective_tier != "free":
            return None
        key = f"DUAL_LOBE_{spec.provider.upper()}_FREE_{kind}"
        raw = os.getenv(key, "").strip()
        try:
            return int(raw) if raw else None
        except ValueError:
            return None

    def _global_limit(self, kind: str) -> int | None:
        raw = os.getenv(f"DUAL_LOBE_MAX_{kind}", "").strip()
        try:
            return int(raw) if raw else None
        except ValueError:
            return None

    def _auto_provider_limit(self, spec: ProviderSpec, kind: str) -> int | None:
        """Known provider/tier limits that can be inferred before the first call.

        Keep this intentionally small. Only encode limits that are documented at
        provider/tier level; model/account-specific limits are learned at runtime
        instead of guessed.
        """
        provider = spec.provider
        tier = spec.effective_tier
        model = spec.model.lower()

        if kind == "RPM" and provider == "openrouter" and tier == "free":
            return 20

        if kind == "RPM" and provider == "groq" and tier == "free":
            if "orpheus" in model:
                return 10
            if "whisper" in model:
                return 20
            return 30

        return None

    def limit_source(self, spec: ProviderSpec, kind: str) -> str:
        learned = self._learned.get(spec.key, LearnedLimit())
        explicit = spec.rpm if kind == "RPM" else spec.tpm
        learned_value = learned.rpm if kind == "RPM" else learned.tpm
        if explicit:
            return "explicit"
        if learned_value:
            return "learned"
        if self._env_free_hint(spec, kind):
            return "provider_tier_override"
        if self._auto_provider_limit(spec, kind):
            return "provider_tier_auto"
        if self._global_limit(kind):
            return "global_fallback"
        return "unknown"

    def limits(self, spec: ProviderSpec) -> tuple[int | None, int | None]:
        learned = self._learned.get(spec.key, LearnedLimit())
        rpm = (
            spec.rpm
            or learned.rpm
            or self._env_free_hint(spec, "RPM")
            or self._auto_provider_limit(spec, "RPM")
            or self._global_limit("RPM")
        )
        tpm = (
            spec.tpm
            or learned.tpm
            or self._env_free_hint(spec, "TPM")
            or self._auto_provider_limit(spec, "TPM")
            or self._global_limit("TPM")
        )
        if rpm:
            rpm = max(1, int(rpm * self.safety))
        if tpm:
            tpm = max(256, int(tpm * self.safety))
        return rpm, tpm

    @staticmethod
    def estimate_input_tokens(text: str) -> int:
        return max(1, (len(text or "") + 3) // 4)

    def fit_output_budget(self, spec: ProviderSpec, input_tokens: int) -> ProviderSpec:
        _, tpm = self.limits(spec)
        if not tpm:
            return spec
        room = tpm - input_tokens - 128
        if room <= 0:
            return replace(spec, max_tokens=256)
        return replace(spec, max_tokens=max(256, min(spec.max_tokens, room)))

    async def acquire(self, spec: ProviderSpec, estimated_tokens: int) -> None:
        """Reserve a request slot and pace calls according to the known max RPM."""
        rpm, tpm = self.limits(spec)
        if not rpm and not tpm:
            return
        key = spec.key
        while True:
            now = time.monotonic()
            wait = 0.0
            with self._lock:
                rq = self._requests[key]
                tq = self._tokens[key]
                while rq and now - rq[0] >= 60:
                    rq.popleft()
                while tq and now - tq[0][0] >= 60:
                    tq.popleft()

                # RPM sensor/pacer: spread requests evenly across the minute
                # instead of allowing a burst up to the rolling-window limit.
                if rpm:
                    next_allowed = self._next_request_at[key]
                    if next_allowed > now:
                        wait = max(wait, next_allowed - now)
                    if len(rq) >= rpm:
                        wait = max(wait, 60 - (now - rq[0]) + 0.02)

                used_tokens = sum(x[1] for x in tq)
                if tpm and used_tokens + estimated_tokens > tpm and tq:
                    wait = max(wait, 60 - (now - tq[0][0]) + 0.02)

                if wait <= 0:
                    rq.append(now)
                    tq.append((now, estimated_tokens))
                    if rpm:
                        self._next_request_at[key] = now + (60.0 / rpm)
                    return
            await asyncio.sleep(min(wait, 60.0))

    def learn_from_error(self, spec: ProviderSpec, exc: Exception) -> LearnedLimit:
        text = str(exc)
        rpm = tpm = None
        retry_after = None
        response = getattr(exc, "response", None)
        headers: Any = getattr(response, "headers", {}) if response is not None else {}
        try:
            get = headers.get
            # Groq documents x-ratelimit-limit-requests as requests/day, not RPM.
            # Do not mislearn that header as an RPM limit.
            if spec.provider != "groq":
                for k in ("x-ratelimit-limit-requests", "ratelimit-limit-requests"):
                    v = get(k)
                    if v:
                        rpm = int(float(v)); break
            for k in ("x-ratelimit-limit-tokens", "ratelimit-limit-tokens"):
                v = get(k)
                if v:
                    tpm = int(float(v)); break
            v = get("retry-after")
            if v:
                retry_after = float(v)
        except Exception:
            pass

        patterns_tpm = [
            r"tokens per minute\s*\(TPM\).*?Limit\s*(\d+)",
            r"TPM\D{0,30}(?:limit\D*)?(\d+)",
            r"token(?:s)? per minute\D{0,30}(\d+)",
        ]
        patterns_rpm = [
            r"requests per minute\s*\(RPM\).*?Limit\s*(\d+)",
            r"RPM\D{0,30}(?:limit\D*)?(\d+)",
            r"request(?:s)? per minute\D{0,30}(\d+)",
        ]
        for pat in patterns_tpm:
            m = re.search(pat, text, flags=re.I | re.S)
            if m:
                tpm = tpm or int(m.group(1)); break
        for pat in patterns_rpm:
            m = re.search(pat, text, flags=re.I | re.S)
            if m:
                rpm = rpm or int(m.group(1)); break
        m = re.search(r"retry(?:-| )after\D{0,20}([0-9.]+)", text, flags=re.I)
        if m:
            retry_after = retry_after or float(m.group(1))

        with self._lock:
            cur = self._learned[spec.key]
            if rpm: cur.rpm = rpm
            if tpm: cur.tpm = tpm
            if retry_after is not None: cur.retry_after_s = retry_after
            cur.learned_at = time.time()
            return LearnedLimit(cur.rpm, cur.tpm, cur.retry_after_s, cur.learned_at)

    @staticmethod
    def classify_error(exc: Exception) -> str:
        s = str(exc).lower()
        status = getattr(exc, "status_code", None)
        if status in {429, 413} or any(x in s for x in ["rate_limit", "rate limit", "tokens per minute", "requests per minute", "tpm", "rpm"]):
            return "rate_limit"
        if status in {500, 502, 503, 504} or any(x in s for x in ["temporarily overloaded", "timeout", "timed out", "connection reset", "service unavailable"]):
            return "transient"
        if status in {401, 403} or "unauthorized" in s or "invalid api key" in s:
            return "auth"
        return "other"

    def retry_delay(self, spec: ProviderSpec, attempt: int) -> float:
        learned = self._learned.get(spec.key)
        if learned and learned.retry_after_s is not None:
            return max(0.1, learned.retry_after_s)
        base = float(os.getenv("DUAL_LOBE_RETRY_BASE_SECONDS", "1.5"))
        cap = float(os.getenv("DUAL_LOBE_RETRY_MAX_SECONDS", "30"))
        return min(cap, base * (2 ** max(0, attempt - 1)))


RATE_CONTROLLER = AdaptiveRateController()
