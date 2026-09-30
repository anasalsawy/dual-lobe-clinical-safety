from __future__ import annotations

import asyncio
import hashlib
import json
import time
from dataclasses import asdict, dataclass, field, replace
from typing import Callable, Sequence

from crewai.tools import BaseTool

from dual_lobe_crewai.runner import run_one
from dual_lobe_crewai.tools import ProxyToolTrace
from dual_lobe_crewai.models import Verdict, AdversarialReview
from dual_lobe_crewai.json_utils import parse_model
from dual_lobe_crewai.prompts import ADVERSARIAL_PROTOCOL, VERIFICATION_PROTOCOL

from .agents import make_b_executor, make_planner, make_b_verifier
from dual_lobe_crewai.tools import make_worker_tools
from .models import ExecutionReport, Plan, PlanContract
from .privacy import PrivacyGuard, PrivacyReceipt, ProviderPrivacyPolicy
from .prompts import (
    build_execution_prompt,
    build_final_review_prompt,
    build_plan_prompt,
    build_revision_prompt,
)
from .tools import (
    CollectExecutionTool,
    ConsultPlannerTool,
    ExecutionDelegateState,
    ExecuteParallelTool,
    collect_all_execution_results,
)


@dataclass
class ClinicalRunResult:
    sanitized_query: str
    sanitized_patient_context: str
    plan: Plan
    plan_revision: int
    plan_sha256: str
    execution_report: str
    delegated_results: str
    answer: str
    verdict: Verdict
    trace_event_count: int = 0
    trace_sha256: str = ""
    timings_ms: dict[str, int | float] = field(default_factory=dict)
    logical_model_calls: int = 0
    privacy_receipt: PrivacyReceipt | None = None

    @property
    def released_answer(self) -> str:
        return self.answer

    def visible_text(self) -> str:
        meter = f"[{self.verdict.deception_level}] {self.verdict.rationale}".strip()
        return f"{self.answer.rstrip()}\n\nDual-Lobe meter: {meter}"


class ClinicalDualLobeEngine:
    """Planner-executor clinical Dual-Lobe runtime.

    A owns reasoning, planning, plan revision, final review, and the user-facing answer.
    B is local, owns tool/data execution, can challenge A at any time, and may parallelize
    independent plan steps.  The current A-authored plan is held by deterministic code as
    the execution contract; B cannot silently rewrite it.
    """

    name = "clinical-planner-executor"

    def __init__(
        self,
        *,
        execution_tools: Sequence[BaseTool] | None = None,
        privacy_guard: PrivacyGuard | None = None,
        provider_privacy_policy: ProviderPrivacyPolicy | None = None,
    ) -> None:
        self.execution_tools = list(execution_tools or [])
        self.privacy_guard = privacy_guard or PrivacyGuard(provider_privacy_policy)

    async def _call(
        self,
        agent,
        prompt: str,
        expected_output: str,
        *,
        role_key: str,
        state_key: str | None = None,
    ) -> str:
        result = await run_one(
            agent,
            prompt,
            expected_output,
            role_key=role_key,
            state_key=state_key,
        )
        text = str(result or "").strip()
        if not text:
            raise RuntimeError(f"{role_key} returned an empty response")
        return text

    async def _make_plan(self, *, query: str, patient_context: str) -> Plan:
        raw = await self._call(
            make_planner(),
            build_plan_prompt(query=query, patient_context=patient_context),
            "Strict JSON full execution plan.",
            role_key="A",
            state_key="clinical:A",
        )
        return Plan.from_text(raw)

    async def _revise_plan(
        self,
        *,
        query: str,
        patient_context: str,
        contract: PlanContract,
        concern: str,
        evidence: str,
    ) -> Plan:
        raw = await self._call(
            make_planner(),
            build_revision_prompt(
                query=query,
                patient_context=patient_context,
                current_plan_json=contract.current_json(),
                concern=concern,
                evidence=evidence,
            ),
            "Strict JSON revised full execution plan.",
            role_key="A",
            state_key="clinical:A",
        )
        return Plan.from_text(raw)

    async def _execute(
        self,
        *,
        raw_query: str,
        raw_patient_context: str,
        contract: PlanContract,
        trace: ProxyToolTrace,
        planner_callback: Callable[[str, str], Plan],
        delegate_state: ExecutionDelegateState,
    ) -> str:
        tools: list[BaseTool] = [
            *self.execution_tools,
            ConsultPlannerTool(
                contract=contract,
                planner_callback=planner_callback,
                trace=trace,
            ),
            ExecuteParallelTool(
                contract=contract,
                raw_query=raw_query,
                raw_patient_context=raw_patient_context,
                execution_tools=self.execution_tools,
                trace=trace,
                run_state=delegate_state,
            ),
            CollectExecutionTool(
                contract=contract,
                trace=trace,
                run_state=delegate_state,
            ),
        ]
        b = make_b_executor(tools=tools)
        return await self._call(
            b,
            build_execution_prompt(
                query=raw_query,
                patient_context=raw_patient_context,
                current_plan_json=contract.current_json(),
                revision=contract.revision,
            ),
            "Strict JSON execution report grounded in the current plan and actual tool results.",
            role_key="B_CLINICAL",
            state_key="clinical:B",
        )

    async def _final_review(
        self,
        *,
        query: str,
        patient_context: str,
        contract: PlanContract,
        execution_report: str,
        delegated_results: str,
        trace_text: str,
    ) -> str:
        return await self._call(
            make_planner(),
            build_final_review_prompt(
                query=query,
                patient_context=patient_context,
                final_plan_json=contract.current_json(),
                plan_revision=contract.revision,
                execution_report=execution_report,
                delegated_results=delegated_results,
                trace_text=trace_text,
            ),
            "A concise user-facing answer that checks execution against the plan.",
            role_key="A",
            state_key="clinical:A",
        )

    async def _b_verify(
        self,
        *,
        query: str,
        patient_context: str,
        a_answer: str,
        contract: PlanContract,
        execution_report: str,
        delegated_results: str,
        trace_text: str,
        trace: ProxyToolTrace,
    ) -> AdversarialReview:
        b_trace = ProxyToolTrace()
        b = make_b_verifier(tools=make_worker_tools(trace=b_trace))
        prompt = f"""You are Lobe B. A has produced a candidate answer. Your job is to attack it adversarially and then verify it. You are NOT the fixer or co-author.

ORIGINAL USER TASK:
{query}

PATIENT CONTEXT:
{patient_context if patient_context else "(none)"}

CURRENT PLAN:
{contract.current_json()}

A'S CANDIDATE ANSWER:
{a_answer}

EXECUTION REPORT:
{execution_report if execution_report else "(none)"}

DELEGATED RESULTS:
{delegated_results if delegated_results else "(none)"}

EXECUTION TRACE:
{trace_text if trace_text else "(no trace)"}

{ADVERSARIAL_PROTOCOL}

{VERIFICATION_PROTOCOL}

Perform this sequence:
1. Attack A's reasoning, feasibility, hidden assumptions, and goal-fit.
2. Ask what the user is not seeing that could change the approach.
3. Ask whether the answer may fail to achieve the user's actual intent.
4. Audit every material claim under the anti-deception protocol.
5. Do NOT repair, rewrite, complete, or improve A's answer. Expose the holes and state what would have to change or be proven.
6. Apply the verdict to A's EXACT answer as it stands.
7. Return A's answer unchanged in final_answer solely as the canonical payload, alongside your independent adversarial findings and verdict.

Return ONLY JSON:
{{
  "final_answer": "A's candidate answer reproduced unchanged",
  "answer_verdict": {{
    "deception_level": "GREEN|YELLOW|RED",
    "rationale": "brief evidence-grounded reason",
    "handoff": {{
      "next_step": "",
      "missing": [],
      "unverified": [],
      "widen": [],
      "memory_query": "",
      "proof_requests": []
    }}
  }},
  "challenges": ["important holes B found"],
  "intent_risks": ["ways this may fail the user's actual goal"],
  "overlooked_context": ["missing facts or perspectives that could change the approach"],
  "delegation_note": "whether delegation was used well, underused, or not applicable"
}}

Do not include a challenge merely to populate a field. Empty lists are correct when nothing material is found."""
        raw = await self._call(
            b,
            prompt,
            "Strict JSON adversarial attack with A's answer unchanged plus anti-deception verdict.",
            role_key="B_CLINICAL_VERIFY",
            state_key="clinical:B_VERIFY",
        )
        fallback = AdversarialReview(
            final_answer=a_answer or "A_AND_B_CALLS_FAILED_OR_EMPTY",
            answer_verdict=Verdict(
                deception_level="YELLOW",
                rationale="B adversarial verification could not be completed or parsed.",
            ),
            challenges=[],
            intent_risks=[],
            overlooked_context=[],
            delegation_note="Verification impaired.",
        )
        review = parse_model(raw, AdversarialReview, fallback)
        review.answer_verdict = self._harden_verdict(review.answer_verdict)

        if b_trace.events:
            trace.add(
                "b_verify_tools",
                input_text="adversarial review and verification",
                output_text=b_trace.render(),
                provenance="lobe_b_verify_trace",
            )
        return review

    @staticmethod
    def _harden_verdict(verdict: Verdict) -> Verdict:
        unresolved = (
            verdict.handoff.missing
            or verdict.handoff.unverified
            or verdict.handoff.proof_requests
        )
        if verdict.deception_level == "GREEN" and unresolved:
            return verdict.model_copy(
                update={
                    "deception_level": "YELLOW",
                    "rationale": (
                        "Material evidence or task gaps remain unresolved; GREEN is not allowed. "
                        + verdict.rationale
                    )[:1600],
                }
            )
        return verdict

    async def run_clinical(
        self,
        *,
        query: str,
        patient_context: str,
        local_delivery: Callable[[str], None] | None = None,
    ) -> ClinicalRunResult:
        started = time.perf_counter()
        timings: dict[str, int | float] = {}
        vault = self.privacy_guard.new_vault()

        sanitized_query, sanitized_context, receipt = self.privacy_guard.prepare(
            query=query,
            patient_context=patient_context,
            vault=vault,
        )

        trace = ProxyToolTrace()
        delegate_state = ExecutionDelegateState()
        execution_report_raw = ""
        delegated_results_raw = ""
        final_answer = ""
        plan: Plan | None = None
        contract: PlanContract | None = None

        try:
            t = time.perf_counter()
            plan = await self._make_plan(
                query=sanitized_query,
                patient_context=sanitized_context,
            )
            timings["a_plan_ms"] = int((time.perf_counter() - t) * 1000)
            contract = PlanContract(plan)
            trace.add(
                "plan_frozen",
                input_text=f"revision={contract.revision}",
                output_text=contract.current_json(),
                provenance="deterministic_plan_contract",
            )

            def planner_callback(concern: str, evidence: str) -> Plan:
                return _run_coro_sync(
                    self._revise_plan(
                        query=sanitized_query,
                        patient_context=sanitized_context,
                        contract=contract,
                        concern=concern,
                        evidence=evidence,
                    )
                )

            t = time.perf_counter()
            execution_report_raw = await self._execute(
                raw_query=query,
                raw_patient_context=patient_context,
                contract=contract,
                trace=trace,
                planner_callback=planner_callback,
                delegate_state=delegate_state,
            )
            timings["b_execute_ms"] = int((time.perf_counter() - t) * 1000)

            delegated_results_raw = await collect_all_execution_results(delegate_state, trace)
            report = ExecutionReport.from_text(execution_report_raw)
            report.assert_matches_contract(contract)

            safe_report, _ = self.privacy_guard.sanitize_trace(execution_report_raw, vault=vault)
            safe_delegated, _ = self.privacy_guard.sanitize_trace(delegated_results_raw, vault=vault)
            safe_trace, trace_phi_types = self.privacy_guard.sanitize_trace(trace.render(), vault=vault)

            receipt = replace(
                receipt,
                direct_identifier_types=tuple(
                    sorted(set(receipt.direct_identifier_types) | set(trace_phi_types))
                ),
                token_count=vault.token_count,
            )

            t = time.perf_counter()
            final_answer = await self._final_review(
                query=sanitized_query,
                patient_context=sanitized_context,
                contract=contract,
                execution_report=safe_report,
                delegated_results=safe_delegated,
                trace_text=safe_trace,
            )
            timings["a_review_ms"] = int((time.perf_counter() - t) * 1000)

            t = time.perf_counter()
            review = await self._b_verify(
                query=sanitized_query,
                patient_context=sanitized_context,
                a_answer=final_answer,
                contract=contract,
                execution_report=safe_report,
                delegated_results=safe_delegated,
                trace_text=safe_trace,
                trace=trace,
            )
            timings["b_verify_ms"] = int((time.perf_counter() - t) * 1000)

            if local_delivery is not None:
                local_delivery(vault.rehydrate_text(review.final_answer))

            trace_sha256 = hashlib.sha256(safe_trace.encode("utf-8")).hexdigest()
            plan_sha256 = contract.fingerprint()
            result = ClinicalRunResult(
                sanitized_query=sanitized_query,
                sanitized_patient_context=sanitized_context,
                plan=contract.current,
                plan_revision=contract.revision,
                plan_sha256=plan_sha256,
                execution_report=safe_report,
                delegated_results=safe_delegated,
                answer=review.final_answer,
                verdict=review.answer_verdict,
                trace_event_count=len(trace.snapshot_from(0)),
                trace_sha256=trace_sha256,
                timings_ms=timings,
                logical_model_calls=4 + contract.revision + delegate_state.child_count,
                privacy_receipt=receipt,
            )
        finally:
            delegate_state.close()
            vault.destroy_key()

        result.privacy_receipt = self.privacy_guard.finalized_receipt(receipt, vault)
        result.timings_ms["total_ms"] = int((time.perf_counter() - started) * 1000)
        return result


def _run_coro_sync(coro):
    """Run an async planner revision from a synchronous CrewAI tool call."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    box: dict[str, object] = {}
    error: list[BaseException] = []

    def worker() -> None:
        try:
            box["value"] = asyncio.run(coro)
        except BaseException as exc:  # propagate into the tool caller
            error.append(exc)

    import threading

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    thread.join()
    if error:
        raise error[0]
    return box["value"]
