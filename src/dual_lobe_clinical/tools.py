from __future__ import annotations

import asyncio
import concurrent.futures
import hashlib
import json
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Sequence, Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from dual_lobe_crewai.runner import run_one
from dual_lobe_crewai.tools import ProxyToolTrace

from .agents import make_b_executor
from .models import Plan, PlanContract


def _run_coro_sync(coro):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    box: dict[str, object] = {}
    errors: list[BaseException] = []

    def worker():
        try:
            box["value"] = asyncio.run(coro)
        except BaseException as exc:
            errors.append(exc)

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    thread.join()
    if errors:
        raise errors[0]
    return box["value"]


class ConsultPlannerInput(BaseModel):
    concern: str = Field(..., min_length=1)
    evidence: str = Field("", description="What B observed that makes the plan questionable.")


class ConsultPlannerTool(BaseTool):
    name: str = "consult_planner"
    description: str = (
        "Challenge the current plan during execution. A reviews the concern and "
        "returns the complete current plan. If A revises it, deterministic code "
        "replaces the plan contract."
    )
    args_schema: Type[BaseModel] = ConsultPlannerInput
    contract: PlanContract
    planner_callback: Callable[[str, str], Plan]
    trace: ProxyToolTrace

    model_config = {"arbitrary_types_allowed": True}

    def _run(self, concern: str, evidence: str = "") -> str:
        old_revision = self.contract.revision
        old_hash = self.contract.fingerprint()
        new_plan = self.planner_callback(concern, evidence)
        new_hash = hashlib.sha256(
            json.dumps(new_plan.model_dump(), ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()
        if new_hash != old_hash:
            revision = self.contract.revise(new_plan, reason=concern)
            outcome = f"PLAN_REVISED revision={revision}\n{self.contract.current_json()}"
        else:
            outcome = f"PLAN_UPHELD revision={old_revision}\n{self.contract.current_json()}"
        self.trace.add(
            "consult_planner",
            input_text=f"concern={concern}\nevidence={evidence}",
            output_text=outcome,
            provenance="b_to_a_live_channel",
        )
        return outcome


@dataclass
class ExecutionJob:
    job_id: str
    step_id: str
    future: concurrent.futures.Future
    launched_perf: float
    collected: bool = False


@dataclass
class ExecutionDelegateState:
    max_children: int = 6
    jobs: dict[str, ExecutionJob] = field(default_factory=dict)
    lock: threading.Lock = field(default_factory=threading.Lock)
    executor: concurrent.futures.ThreadPoolExecutor = field(init=False, repr=False)

    def __post_init__(self):
        self.executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_children,
            thread_name_prefix="clinical-b-exec",
        )

    @property
    def child_count(self) -> int:
        with self.lock:
            return len(self.jobs)

    def close(self) -> None:
        self.executor.shutdown(wait=False, cancel_futures=False)


class ExecuteParallelInput(BaseModel):
    step_ids: list[str] = Field(..., min_length=1)


class ExecuteParallelTool(BaseTool):
    name: str = "execute_parallel"
    description: str = (
        "Launch independent current-plan steps concurrently on temporary local B "
        "execution instances. Only steps marked parallelizable in A's current plan "
        "may be launched."
    )
    args_schema: Type[BaseModel] = ExecuteParallelInput
    contract: PlanContract
    raw_query: str
    raw_patient_context: str
    execution_tools: Sequence[BaseTool]
    trace: ProxyToolTrace
    run_state: ExecutionDelegateState

    model_config = {"arbitrary_types_allowed": True}

    def _run(self, step_ids: list[str]) -> str:
        requested = []
        for step_id in step_ids:
            step = self.contract.step(step_id)
            if not step.parallelizable:
                return f"PARALLEL_EXECUTION_REJECTED: {step_id} is not marked parallelizable."
            if step.depends_on:
                return (
                    f"PARALLEL_EXECUTION_REJECTED: {step_id} has dependencies {step.depends_on}; "
                    "run it after those dependencies are satisfied."
                )
            requested.append(step)

        launched: list[str] = []
        for step in requested:
            with self.run_state.lock:
                if len(self.run_state.jobs) >= self.run_state.max_children:
                    break
                job_id = f"b-child-{len(self.run_state.jobs) + 1}"

            plan_json = self.contract.current_json()
            revision = self.contract.revision

            def work(step=step, plan_json=plan_json, revision=revision):
                child = make_b_executor(tools=list(self.execution_tools))
                prompt = f"""You are a temporary local execution instance of Lobe B.

USER TASK:
{self.raw_query}

LOCAL CLINICAL DATA / CONTEXT:
{self.raw_patient_context}

PLAN REVISION: {revision}
FULL PLAN:
{plan_json}

YOUR ASSIGNED STEP:
{step.id}: {step.action}

Execute only this step. Do not rewrite the plan and do not speak to the user.
Return the actual result and any tool evidence or failure."""
                return _run_coro_sync(
                    run_one(
                        child,
                        prompt,
                        "A self-contained execution result for the assigned plan step.",
                        role_key="B_CLINICAL",
                        persistent_state=False,
                    )
                )

            future = self.run_state.executor.submit(work)
            with self.run_state.lock:
                self.run_state.jobs[job_id] = ExecutionJob(
                    job_id=job_id,
                    step_id=step.id,
                    future=future,
                    launched_perf=time.perf_counter(),
                )
            launched.append(job_id)

        result = (
            "PARALLEL_EXECUTION_STARTED: " + ", ".join(launched)
            if launched
            else "PARALLEL_EXECUTION_REJECTED: no child capacity."
        )
        self.trace.add(
            "execute_parallel",
            input_text="step_ids=" + ",".join(step_ids),
            output_text=result,
            provenance="b_parallel_execution",
        )
        return result


class CollectExecutionInput(BaseModel):
    job_ids: list[str] = Field(default_factory=list)
    wait: bool = True


class CollectExecutionTool(BaseTool):
    name: str = "collect_execution"
    description: str = "Collect results from B's parallel execution instances."
    args_schema: Type[BaseModel] = CollectExecutionInput
    trace: ProxyToolTrace
    run_state: ExecutionDelegateState

    model_config = {"arbitrary_types_allowed": True}

    def _run(self, job_ids: list[str] | None = None, wait: bool = True) -> str:
        ids = list(job_ids or [])
        with self.run_state.lock:
            if not ids:
                ids = list(self.run_state.jobs)
            jobs = [self.run_state.jobs[x] for x in ids if x in self.run_state.jobs]

        if not jobs:
            return "NO_PARALLEL_EXECUTION_JOBS"

        rows = []
        for job in jobs:
            if not wait and not job.future.done():
                rows.append(f"{job.job_id} ({job.step_id}): PENDING")
                continue
            try:
                result = str(job.future.result())
            except Exception as exc:
                result = f"FAILED: {type(exc).__name__}: {exc}"
            rows.append(f"{job.job_id} ({job.step_id}):\n{result}")
            if not job.collected:
                self.trace.add(
                    f"{job.job_id}_result",
                    input_text=job.step_id,
                    output_text=result,
                    provenance="b_parallel_execution_result",
                )
                job.collected = True
        return "\n\n".join(rows)


async def collect_all_execution_results(
    run_state: ExecutionDelegateState,
    trace: ProxyToolTrace,
) -> str:
    with run_state.lock:
        if not run_state.jobs:
            return ""
    collector = CollectExecutionTool(trace=trace, run_state=run_state)
    return await asyncio.to_thread(collector._run, [], True)
