from __future__ import annotations

import asyncio
import hashlib
import json
import time
from dataclasses import asdict, dataclass, field, replace
from typing import Callable

from dual_lobe_crewai.agents import make_b_adversary
from dual_lobe_crewai.engines import DualLobeEngine
from dual_lobe_crewai.live_b import LiveBMonitor
from dual_lobe_crewai.tools import (
    DelegateRunState,
    LiveBState,
    ProxyToolTrace,
    collect_all_delegate_results,
    make_worker_tools,
)

from .control_gate import SafetyGate
from .parsing import assessment_from_json, merge_assessments
from .prompts import build_final_audit_prompt, build_independent_prompt
from .schemas import Decision, GateResult, SupervisorAssessment
from .privacy import (
    EphemeralClinicalMemory,
    PrivacyGuard,
    PrivacyReceipt,
    ProviderPrivacyPolicy,
)


@dataclass
class ClinicalRunResult:
    sanitized_query: str
    sanitized_patient_context: str
    candidate_answer: str
    released_answer: str | None
    gate: GateResult
    independent_assessment: SupervisorAssessment
    final_assessment: SupervisorAssessment
    merged_assessment: SupervisorAssessment
    supervisory_context_supplied: bool = False
    supervisory_context_sha256: str = ""
    trace_event_count: int = 0
    trace_sha256: str = ""
    timings_ms: dict[str, int | float] = field(default_factory=dict)
    logical_model_calls: int = 0
    privacy_receipt: PrivacyReceipt | None = None
    privacy_trace_identifier_types: tuple[str, ...] = ()

    @property
    def blocked(self) -> bool:
        return self.released_answer is None


class ClinicalDualLobeEngine(DualLobeEngine):
    """Clinical Dual-Lobe runtime.

    B first forms an independent pre-answer safety view from the original
    context plus any additional supervisory information supplied by the runtime.
    B later audits A's exact answer and observable execution/provenance trace.
    Deterministic code owns the release decision.
    """

    name = "dual-lobe-clinical"

    def __init__(
        self,
        *,
        supervisory_context_provider: Callable[[str, str], str] | None = None,
        memory=None,
        b_memory=None,
        privacy_guard: PrivacyGuard | None = None,
        provider_privacy_policy: ProviderPrivacyPolicy | None = None,
        enable_live_b: bool = True,
    ):
        if memory is None:
            memory = EphemeralClinicalMemory()
        if b_memory is None:
            b_memory = EphemeralClinicalMemory()
        super().__init__(memory=memory, b_memory=b_memory)
        self.privacy_guard = privacy_guard or PrivacyGuard(provider_privacy_policy)
        self.enable_live_b = bool(enable_live_b)
        self.supervisory_context_provider = supervisory_context_provider
        self.gate = SafetyGate()

    def _supervisory_context(self, *, query: str, patient_context: str) -> str:
        if self.supervisory_context_provider is None:
            return ""
        value = self.supervisory_context_provider(query, patient_context)
        return str(value or "").strip()

    async def _independent_pass(
        self,
        *,
        query: str,
        patient_context: str,
        supervisory_context: str,
    ) -> SupervisorAssessment:
        b = make_b_adversary(tools=None, llm_role="B_CLINICAL")
        prompt = build_independent_prompt(
            query=query,
            patient_context=patient_context,
            supervisory_context=supervisory_context,
        )
        raw = await self._safe_run_one(
            b,
            prompt,
            "Strict JSON independent clinical-safety assessment.",
            fallback_text='{"supervisor_claims_grounded": false, "notes": ["independent B pass failed"]}',
            role_key="B_CLINICAL",
        )
        return assessment_from_json(raw)

    async def _final_clinical_audit(
        self,
        *,
        query: str,
        patient_context: str,
        a_answer: str,
        independent: SupervisorAssessment,
        trace_text: str,
        delegated_results: str,
        supervisory_context: str,
        privacy_receipt_json: str,
        privacy_trace_identifier_types: str,
    ) -> SupervisorAssessment:
        b_trace = ProxyToolTrace()
        b = make_b_adversary(
            tools=make_worker_tools(self.b_memory, trace=b_trace),
            llm_role="B_CLINICAL",
        )
        prior = json.dumps(asdict(independent), indent=2)
        prompt = build_final_audit_prompt(
            query=query,
            patient_context=patient_context,
            independent_json=prior,
            a_answer=a_answer,
            delegated_results=delegated_results,
            trace_text=trace_text,
            supervisory_context=supervisory_context,
            privacy_receipt_json=privacy_receipt_json,
            privacy_trace_identifier_types=privacy_trace_identifier_types,
        )
        raw = await self._safe_run_one(
            b,
            prompt,
            "Strict JSON final clinical adversarial audit with claim ledger.",
            fallback_text='{"supervisor_claims_grounded": false, "notes": ["final B audit failed"]}',
            role_key="B_CLINICAL",
        )
        return assessment_from_json(raw)

    @staticmethod
    def _release(candidate: str, gate: GateResult) -> str | None:
        if gate.decision in {Decision.PASS, Decision.WARN}:
            return candidate
        return None

    async def run_clinical(
        self,
        *,
        query: str,
        patient_context: str,
        local_delivery: Callable[[str], None] | None = None,
    ) -> ClinicalRunResult:
        total_start = time.perf_counter()
        timings: dict[str, int | float] = {}

        vault = self.privacy_guard.new_vault()
        sanitized_query, sanitized_context, privacy_receipt = self.privacy_guard.prepare(
            query=query,
            patient_context=patient_context,
            vault=vault,
        )

        original_task = (
            "CLINICAL RESEARCH TASK\n"
            f"PATIENT_CONTEXT:\n{sanitized_context}\n\n"
            f"QUERY:\n{sanitized_query}"
        )
        a_memory = self.memory.auto_slice(original_task)
        strategy_memory = self.memory.split_experience_slice(original_task, limit=3, max_chars=3000)
        trace = ProxyToolTrace()
        delegate_state = DelegateRunState()
        live_b_state = LiveBState()

        supervisory_context = self._supervisory_context(
            query=sanitized_query,
            patient_context=sanitized_context,
        )
        context_hash = hashlib.sha256(supervisory_context.encode("utf-8")).hexdigest() if supervisory_context else ""

        live_monitor = LiveBMonitor(
            task=original_task,
            b_memory=self.b_memory,
            trace=trace,
            state=live_b_state,
            role_key="B_CLINICAL",
        ) if self.enable_live_b else None
        live_task = asyncio.create_task(live_monitor.run()) if live_monitor else None

        independent_start = time.perf_counter()
        independent_task = asyncio.create_task(
            self._independent_pass(
                query=sanitized_query,
                patient_context=sanitized_context,
                supervisory_context=supervisory_context,
            )
        )

        try:
            a_start = time.perf_counter()
            a_answer = await self._run_a(
                task=original_task,
                memory_slice=a_memory,
                strategy_memory=strategy_memory,
                canonical_state="",
                trace=trace,
                delegate_state=delegate_state,
                live_b_state=live_b_state,
            )
            timings["a_ms"] = int((time.perf_counter() - a_start) * 1000)

            delegated_results = await collect_all_delegate_results(delegate_state, trace)

            if live_monitor is not None and live_task is not None:
                live_monitor.stop()
                await live_task
                timings["b_live_calls"] = live_monitor.calls
            else:
                timings["b_live_calls"] = 0

            independent = await independent_task
            timings["b_independent_ms"] = int((time.perf_counter() - independent_start) * 1000)

            raw_trace_text = trace.render()
            trace_text, trace_phi_types = self.privacy_guard.sanitize_trace(raw_trace_text, vault=vault)
            delegated_results, delegated_phi_types = self.privacy_guard.sanitize_trace(delegated_results, vault=vault)
            privacy_trace_types = tuple(sorted(set(trace_phi_types) | set(delegated_phi_types)))
            trace_events = trace.snapshot_from(0)
            trace_sha256 = hashlib.sha256(trace_text.encode("utf-8")).hexdigest()

            privacy_receipt = replace(
                privacy_receipt,
                direct_identifier_types=tuple(
                    sorted(set(privacy_receipt.direct_identifier_types) | set(privacy_trace_types))
                ),
                token_count=vault.token_count,
            )
            privacy_receipt_json = json.dumps(
                asdict(privacy_receipt),
                default=lambda x: x.value if hasattr(x, "value") else str(x),
                sort_keys=True,
            )

            audit_start = time.perf_counter()
            final_assessment = await self._final_clinical_audit(
                query=sanitized_query,
                patient_context=sanitized_context,
                a_answer=a_answer,
                independent=independent,
                trace_text=trace_text,
                delegated_results=delegated_results,
                supervisory_context=supervisory_context,
                privacy_receipt_json=privacy_receipt_json,
                privacy_trace_identifier_types=", ".join(privacy_trace_types) or "none",
            )
            timings["b_final_audit_ms"] = int((time.perf_counter() - audit_start) * 1000)

            merged = merge_assessments(independent, final_assessment)
            gate_result = self.gate.evaluate(merged)
            released = self._release(a_answer, gate_result)

            if released is not None and local_delivery is not None:
                local_delivery(vault.rehydrate_text(released))
        finally:
            if live_monitor is not None:
                live_monitor.stop()
            if live_task is not None and not live_task.done():
                await live_task
            if not independent_task.done():
                independent_task.cancel()
            delegate_state.close()
            vault.destroy_key()

        privacy_receipt = self.privacy_guard.finalized_receipt(privacy_receipt, vault)
        timings["total_ms"] = int((time.perf_counter() - total_start) * 1000)

        return ClinicalRunResult(
            sanitized_query=sanitized_query,
            sanitized_patient_context=sanitized_context,
            candidate_answer=a_answer,
            released_answer=released,
            gate=gate_result,
            independent_assessment=independent,
            final_assessment=final_assessment,
            merged_assessment=merged,
            supervisory_context_supplied=bool(supervisory_context),
            supervisory_context_sha256=context_hash,
            trace_event_count=len(trace_events),
            trace_sha256=trace_sha256,
            timings_ms=timings,
            logical_model_calls=3 + delegate_state.child_count + (live_monitor.calls if live_monitor else 0),
            privacy_receipt=privacy_receipt,
            privacy_trace_identifier_types=privacy_trace_types,
        )
