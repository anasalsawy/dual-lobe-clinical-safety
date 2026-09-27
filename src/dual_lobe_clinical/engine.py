from __future__ import annotations

import asyncio
import hashlib
import json
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

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
from .evidence import FrozenEvidenceStore
from .parsing import assessment_from_json, merge_assessments
from .prompts import CLINICAL_ADVERSARIAL_AUDIT, CLINICAL_INDEPENDENT_PASS
from .schemas import Decision, GateResult, SupervisorAssessment


@dataclass
class ClinicalRunResult:
    query: str
    patient_context: str
    candidate_answer: str
    released_answer: str | None
    gate: GateResult
    independent_assessment: SupervisorAssessment
    final_assessment: SupervisorAssessment
    merged_assessment: SupervisorAssessment
    retrieved_evidence_ids: tuple[str, ...] = ()
    trace_event_count: int = 0
    trace_sha256: str = ""
    timings_ms: dict[str, int | float] = field(default_factory=dict)
    logical_model_calls: int = 0

    @property
    def blocked(self) -> bool:
        return self.released_answer is None


class ClinicalDualLobeEngine(DualLobeEngine):
    """Publication-oriented clinical safety runtime.

    B performs two distinct jobs:
    1) an independent, pre-answer safety pass that cannot be anchored by A;
    2) a final claim-by-claim adversarial audit of A plus the complete observable
       execution/provenance trace.

    Deterministic code then decides whether A's answer may be released.
    """

    name = "dual-lobe-clinical"

    def __init__(
        self,
        *,
        evidence_store: FrozenEvidenceStore | None = None,
        evidence_path: str | Path | None = None,
        memory=None,
        b_memory=None,
    ):
        super().__init__(memory=memory, b_memory=b_memory)
        if evidence_store is not None:
            self.evidence = evidence_store
        else:
            path = Path(
                evidence_path
                or os.getenv("DUAL_LOBE_CLINICAL_EVIDENCE", "evidence/evidence_manifest.json")
            )
            self.evidence = (
                FrozenEvidenceStore.load_json(path)
                if path.exists()
                else FrozenEvidenceStore()
            )
        self.gate = SafetyGate(self.evidence)

    def _retrieve_evidence(self, *, query: str, patient_context: str):
        search_text = f"{query}\n{patient_context}"
        return self.evidence.retrieve(search_text, limit=12)

    async def _independent_pass(
        self,
        *,
        query: str,
        patient_context: str,
        evidence_text: str,
    ) -> SupervisorAssessment:
        b = make_b_adversary(tools=None)
        prompt = f"""{CLINICAL_INDEPENDENT_PASS}

ORIGINAL CLINICIAN/USER QUERY:
{query}

SUPPLIED PATIENT / CLINICAL CONTEXT:
{patient_context if patient_context else "(none supplied)"}

FROZEN RETRIEVED EVIDENCE:
{evidence_text}

You are intentionally NOT being shown A's answer or A's execution.
Form the independent safety obligations now."""
        raw = await self._safe_run_one(
            b,
            prompt,
            "Strict JSON independent clinical-safety assessment.",
            fallback_text='{"supervisor_claims_grounded": false, "notes": ["independent B pass failed"]}',
            role_key="B_VERIFY",
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
        evidence_text: str,
    ) -> SupervisorAssessment:
        b_trace = ProxyToolTrace()
        b = make_b_adversary(tools=make_worker_tools(self.b_memory, trace=b_trace))
        prior = json.dumps(asdict(independent), indent=2)
        prompt = f"""{CLINICAL_ADVERSARIAL_AUDIT}

ORIGINAL CLINICIAN/USER QUERY:
{query}

SUPPLIED PATIENT / CLINICAL CONTEXT:
{patient_context if patient_context else "(none supplied)"}

B'S PRE-ANSWER INDEPENDENT SAFETY ASSESSMENT:
{prior}

A'S EXACT CANDIDATE ANSWER:
{a_answer}

DELEGATED CHILD RESULTS:
{delegated_results if delegated_results else "(none)"}

COMPLETE OBSERVABLE A/CHILD EXECUTION + PROVENANCE TRACE:
{trace_text if trace_text else "(no observable runtime events)"}

FROZEN RETRIEVED EVIDENCE:
{evidence_text}

Audit A meticulously. Do not treat agreement between A and B as evidence.
Every material A clinical claim must appear in claim_audits."""
        raw = await self._safe_run_one(
            b,
            prompt,
            "Strict JSON final clinical adversarial audit with claim ledger.",
            fallback_text='{"supervisor_claims_grounded": false, "notes": ["final B audit failed"]}',
            role_key="B_VERIFY",
        )
        if b_trace.events:
            # B's own tool activity is evidence about the audit itself. It is
            # intentionally not inserted into A's historical trace fingerprint.
            pass
        return assessment_from_json(raw)

    @staticmethod
    def _release(candidate: str, gate: GateResult) -> str | None:
        # Research runtime is fail-closed for any unresolved material concern.
        if gate.decision in {Decision.PASS, Decision.WARN}:
            return candidate
        return None

    async def run_clinical(
        self,
        *,
        query: str,
        patient_context: str,
    ) -> ClinicalRunResult:
        total_start = time.perf_counter()
        timings: dict[str, int | float] = {}

        original_task = (
            "CLINICAL RESEARCH TASK\n"
            f"PATIENT_CONTEXT:\n{patient_context}\n\n"
            f"QUERY:\n{query}"
        )
        a_memory = self.memory.auto_slice(original_task)
        strategy_memory = self.memory.split_experience_slice(original_task, limit=3, max_chars=3000)
        trace = ProxyToolTrace()
        delegate_state = DelegateRunState()
        live_b_state = LiveBState()

        retrieved = self._retrieve_evidence(query=query, patient_context=patient_context)
        evidence_text = self.evidence.render(retrieved)
        retrieved_ids = tuple(r.evidence_id for r in retrieved)

        live_monitor = LiveBMonitor(
            task=original_task,
            b_memory=self.b_memory,
            trace=trace,
            state=live_b_state,
        )
        live_task = asyncio.create_task(live_monitor.run())

        # This starts BEFORE A's answer exists. It cannot be anchored by A.
        independent_start = time.perf_counter()
        independent_task = asyncio.create_task(
            self._independent_pass(
                query=query,
                patient_context=patient_context,
                evidence_text=evidence_text,
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

            live_monitor.stop()
            await live_task
            timings["b_live_calls"] = live_monitor.calls

            independent = await independent_task
            timings["b_independent_ms"] = int((time.perf_counter() - independent_start) * 1000)

            # Freeze A's observable run before the final audit. The exact text and
            # hash are preserved so the publication can show what B actually saw.
            trace_text = trace.render()
            trace_events = trace.snapshot_from(0)
            trace_sha256 = hashlib.sha256(trace_text.encode("utf-8")).hexdigest()

            audit_start = time.perf_counter()
            final_assessment = await self._final_clinical_audit(
                query=query,
                patient_context=patient_context,
                a_answer=a_answer,
                independent=independent,
                trace_text=trace_text,
                delegated_results=delegated_results,
                evidence_text=evidence_text,
            )
            timings["b_final_audit_ms"] = int((time.perf_counter() - audit_start) * 1000)

            merged = merge_assessments(independent, final_assessment)
            gate_result = self.gate.evaluate(merged)
            released = self._release(a_answer, gate_result)
        finally:
            live_monitor.stop()
            if not live_task.done():
                await live_task
            if not independent_task.done():
                independent_task.cancel()
            delegate_state.close()

        timings["total_ms"] = int((time.perf_counter() - total_start) * 1000)

        return ClinicalRunResult(
            query=query,
            patient_context=patient_context,
            candidate_answer=a_answer,
            released_answer=released,
            gate=gate_result,
            independent_assessment=independent,
            final_assessment=final_assessment,
            merged_assessment=merged,
            retrieved_evidence_ids=retrieved_ids,
            trace_event_count=len(trace_events),
            trace_sha256=trace_sha256,
            timings_ms=timings,
            logical_model_calls=3 + delegate_state.child_count + live_monitor.calls,
        )
