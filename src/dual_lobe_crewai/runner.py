from __future__ import annotations

import asyncio
import os
import threading

from crewai import Crew, Process, Task

from .llm_factory import make_llm, resolve_role_specs
from .provider_control import RATE_CONTROLLER
from .inference_state import CONTINUITY_SNAPSHOTS, NATIVE_INFERENCE_STATE


_RR_LOCK = threading.Lock()
_RR_INDEX: dict[str, int] = {}


def _round_robin_specs(role_key: str, specs):
    """Rotate a role's configured providers so each call starts on the next one."""
    if len(specs) <= 1:
        return list(specs)
    with _RR_LOCK:
        start = _RR_INDEX.get(role_key, 0) % len(specs)
        _RR_INDEX[role_key] = (start + 1) % len(specs)
    return list(specs[start:]) + list(specs[:start])


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
    state_key: str | None = None,
    persistent_state: bool = True,
) -> str:
    role_key = (role_key or _infer_role_key(agent)).upper()
    if persistent_state:
        state_key = state_key or role_key
    else:
        state_key = None
    continuity = CONTINUITY_SNAPSHOTS.context(state_key)
    effective_description = (
        description
        if not continuity
        else continuity + "\n\nCURRENT REQUEST:\n" + description
    )

    specs = _round_robin_specs(role_key, resolve_role_specs(role_key))
    if not specs:
        raise RuntimeError("No LLM providers configured")

    # Round-robin start point for each logical call. If the selected provider
    # errors, immediately try the next provider in the same cyclic order.
    last_exc = None
    for original_spec in specs:
        await RATE_CONTROLLER.ensure_discovered(original_spec)
        input_est = RATE_CONTROLLER.estimate_input_tokens(effective_description + "\n" + expected_output)
        spec = RATE_CONTROLLER.fit_output_budget(original_spec, input_est)
        estimated_total = input_est + spec.max_tokens
        await RATE_CONTROLLER.acquire(spec, estimated_total)

        native_state = await NATIVE_INFERENCE_STATE.prepare(
            base_url=spec.base_url,
            state_key=state_key,
        )
        _set_llm(
            agent,
            make_llm(
                role_key,
                spec=spec,
                extra_body=native_state.extra_body if native_state else None,
            ),
        )

        try:
            out = await _single_call(agent, effective_description, expected_output)
            if out is None or not str(out).strip():
                raise ValueError("Invalid response from LLM call - None or empty.")
            await NATIVE_INFERENCE_STATE.checkpoint(native_state)
            CONTINUITY_SNAPSHOTS.checkpoint(state_key, description, str(out))
            return str(out)
        except Exception as exc:
            NATIVE_INFERENCE_STATE.release(native_state)
            RATE_CONTROLLER.learn_from_error(spec, exc)
            last_exc = exc
            continue

    if last_exc is not None:
        raise last_exc
    raise RuntimeError("No LLM providers available")