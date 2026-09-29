from __future__ import annotations

import time
from dataclasses import replace

from .engines import DualLobeEngine, RunResult, _parse_b_rewrite_test


class RewriteExperimentEngine(DualLobeEngine):
    """Controlled owner experiment layered over the normal Dual-Lobe runtime."""

    async def _record_rewritten_state(self, task: str, result: RunResult) -> None:
        await self._persist_memories(
            task=task,
            review=type("_Review", (), {
                "final_answer": result.answer,
                "answer_verdict": result.verdict,
                "challenges": result.challenges,
                "intent_risks": result.intent_risks,
                "overlooked_context": result.overlooked_context,
            })(),
        )

    async def run(self, task: str) -> RunResult:
        enabled, clean_task, instruction = _parse_b_rewrite_test(task)
        if not enabled:
            return await super().run(task)

        # Run A and the ordinary dual-lobe path only on the cleaned request.
        original_persist = self._persist_memories

        async def no_persist(*, task, review):
            return None

        self._persist_memories = no_persist
        try:
            base = await super().run_cycle(clean_task)
        finally:
            self._persist_memories = original_persist

        started = time.perf_counter()
        rewritten = await self._run_b_rewrite_test(
            clean_task=clean_task,
            instruction=instruction,
            a_answer=base.answer,
        )
        timings = dict(base.timings_ms)
        timings["b_rewrite_test_ms"] = int((time.perf_counter() - started) * 1000)

        result = replace(
            base,
            answer=rewritten,
            canonical_state=rewritten,
            timings_ms=timings,
            logical_model_calls=base.logical_model_calls + 1,
        )

        # Only the rewritten assistant state is committed to A's persistent memory.
        await original_persist(
            task=clean_task,
            review=type("_Review", (), {
                "final_answer": rewritten,
                "answer_verdict": result.verdict,
                "challenges": result.challenges,
                "intent_risks": result.intent_risks,
                "overlooked_context": result.overlooked_context,
            })(),
        )
        return result

    async def run_loop(self, task: str, *, cycles: int) -> list[RunResult]:
        if cycles < 1:
            raise ValueError("cycles must be >= 1")

        enabled, clean_task, instruction = _parse_b_rewrite_test(task)
        if not enabled:
            return await super().run_loop(task, cycles=cycles)

        first = await self.run(task)
        results = [first]
        canonical_state = first.canonical_state or first.answer

        for cycle_index in range(2, cycles + 1):
            result = await super().run_cycle(
                clean_task,
                canonical_state=canonical_state,
                cycle_index=cycle_index,
            )
            results.append(result)
            canonical_state = result.canonical_state or result.answer
        return results
