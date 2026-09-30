from __future__ import annotations

import asyncio
import os
import threading
from typing import Callable

from crewai import Crew, Process, Task

from .llm_factory import make_llm, resolve_role_specs
from .provider_control import RATE_CONTROLLER, ProviderSpec


class EgressDenied(RuntimeError):
    """Raised by an egress filter to refuse sending a payload to a destination."""


EgressFilter = Callable[[ProviderSpec, str], str]
_EGRESS_FILTERS: list[EgressFilter] = []

# (role, provider label, model) of every successful call, so callers can record which provider actually served.
SERVED_CALLS: list[tuple[str, str, str]] = []
_RR_LOCK = threading.Lock()
_RR_POOL: list = []
_RR_NEXT = 0


def _rr_reset() -> None:
    global _RR_NEXT
    with _RR_LOCK:
        _RR_POOL.clear()
        _RR_NEXT = 0


def _spec_id(spec):
    # Same model at the same host under different API keys counts as a separate slot.
    if hasattr(spec, "model"):
        return (spec.model, spec.base_url, spec.api_key)
    return spec.label


def _round_robin_specs(role_key: str, specs):
    """Rotate one shared provider cycle across all calls (1,2,3,1,2,3...), regardless of role.

    A role that lacks the next provider in the cycle starts on the next one it has.
    """
    global _RR_NEXT
    specs = list(specs)
    if len(specs) <= 1:
        return specs
    ids = [_spec_id(s) for s in specs]
    with _RR_LOCK:
        for sid in ids:
            if sid not in _RR_POOL:
                _RR_POOL.append(sid)
        n = len(_RR_POOL)
        start = 0
        for step in range(n):
            target = _RR_POOL[(_RR_NEXT + step) % n]
            if target in ids:
                start = ids.index(target)
                _RR_NEXT = (_RR_NEXT + step + 1) % n
                break
    return specs[start:] + specs[:start]


def register_egress_filter(fn: EgressFilter) -> None:
    """Install a filter applied to every prompt before it is sent to a provider.

    A filter receives the destination spec and the outbound text and returns the
    text to send, or raises EgressDenied. The generic runtime installs none.
    """
    if fn not in _EGRESS_FILTERS:
        _EGRESS_FILTERS.append(fn)


def unregister_egress_filter(fn: EgressFilter) -> None:
    if fn in _EGRESS_FILTERS:
        _EGRESS_FILTERS.remove(fn)


def apply_egress_filters(spec: ProviderSpec, text: str) -> str:
    for fn in list(_EGRESS_FILTERS):
        text = fn(spec, text)
    return text


def _infer_role_key(agent) -> str:
    role = str(getattr(agent, "role", "")).lower()
    if "adversary" in role or "verification" in role or "verifier" in role or "lobe b" in role:
        return "B_VERIFY"
    if "delegated inference worker" in role or "temporary delegated" in role:
        return "A_CHILD"
    return "A"


def _set_llm(agent, llm):
    try:
        agent.llm = llm
    except Exception:
        object.__setattr__(agent, "llm", llm)


async def _single_call(agent, description: str, expected_output: str) -> str:
    task = Task(description=description, expected_output=expected_output, agent=agent)
    crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False)
    result = await crew.kickoff_async()
    raw = getattr(result, "raw", None)
    return str(raw if raw is not None else result)


async def run_one(
    agent,
    description: str,
    expected_output: str,
    *,
    role_key: str | None = None,
    specs: list[ProviderSpec] | None = None,
) -> str:
    role_key = (role_key or _infer_role_key(agent)).upper()
    specs = _round_robin_specs(role_key, list(specs) if specs else resolve_role_specs(role_key))
    max_rounds = max(1, int(os.getenv("DUAL_LOBE_RETRY_ROUNDS", "3")))
    failover = os.getenv("DUAL_LOBE_FAILOVER_ON_RATE_LIMIT", "true").lower() in {"1", "true", "yes", "on"}
    last_exc = None

    for round_no in range(1, max_rounds + 1):
        candidates = specs if (round_no == 1 or failover) else specs[:1]
        for idx, original_spec in enumerate(candidates):
            try:
                guarded_description = apply_egress_filters(original_spec, description)
                guarded_expected = apply_egress_filters(original_spec, expected_output)
            except EgressDenied as exc:
                # Never retried against the same destination; another candidate
                # (e.g. a local one) may still be acceptable.
                last_exc = exc
                continue
            spec = original_spec
            try:
                input_est = RATE_CONTROLLER.estimate_input_tokens(guarded_description + "\n" + guarded_expected)
                spec = RATE_CONTROLLER.fit_output_budget(original_spec, input_est)
                estimated_total = input_est + spec.max_tokens
                await RATE_CONTROLLER.acquire(spec, estimated_total)
                _set_llm(agent, make_llm(role_key, spec=spec))
                out = await _single_call(agent, guarded_description, guarded_expected)
                if out is None or not str(out).strip():
                    raise ValueError("Invalid response from LLM call - None or empty.")
                SERVED_CALLS.append((role_key, spec.label, spec.model))
                return str(out)
            except Exception as exc:
                last_exc = exc
                kind = RATE_CONTROLLER.classify_error(exc)
                RATE_CONTROLLER.learn_from_error(spec, exc)
                if idx + 1 < len(candidates):
                    continue
                if kind not in {"rate_limit", "transient"}:
                    break

        if isinstance(last_exc, EgressDenied):
            break
        if round_no < max_rounds and last_exc is not None:
            await asyncio.sleep(RATE_CONTROLLER.retry_delay(specs[0], round_no))

    if last_exc is not None:
        raise last_exc
    raise RuntimeError("No LLM candidates available")
