"""Clinical Dual-Lobe engine.

    clinician question + patient record (raw, stays in-process)
            |
            v
    PrivacySession ---- de-identified view ----------------------------+
      |  (local B residual sweep; egress monitor on every call)        |
      v                                                                v
    Lobe A (may be remote; sees de-identified view only)      Lobe B context scan (local;
      + delegated children, optional live B                     runs concurrently, never sees A's answer)
      |                                                                |
      +----------------------> Lobe B final audit (local) <------------+
                                     |
                         deterministic grounding + release gate
                                     |
                 rehydrate for the clinician, destroy the session key

A is the unmodified generic Dual-Lobe worker. B keeps its generic adversarial
persona and anti-deception protocol, plus a clinical mandate: read the whole
record, not just the part the question touches.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import time
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from crewai import Agent
from pydantic import BaseModel

from dual_lobe_crewai.agents import make_b_adversary
from dual_lobe_crewai.engines import DualLobeEngine
from dual_lobe_crewai.json_utils import extract_json_object
from dual_lobe_crewai.live_b import LiveBMonitor
from dual_lobe_crewai.llm_factory import make_llm
from dual_lobe_crewai.memory import JsonlMemoryStore, MemoryEntry
from dual_lobe_crewai.models import Verdict
from dual_lobe_crewai.prompts import VERIFICATION_PROTOCOL
from dual_lobe_crewai.runner import run_one
from dual_lobe_crewai.tools import DelegateRunState, LiveBState, ProxyToolTrace, collect_all_delegate_results

from . import egress
from .control import GateDecision, GroundedFinding, decide, ground_all, normalize_ref
from .egress import EGRESS_MONITOR
from .knowledge import KnowledgeSource, Snippet, from_env as knowledge_from_env, render as render_knowledge, retrieve_for_view
from .locality import LocalityError, locality_mode, resolve_b_specs
from .models import ClinicalFinding, ClinicalReview, ContextScan, Release, ResidualSweep, Supervision
from .privacy import ClinicalView, PrivacyReceipt, PrivacySession, find_tokens
from .prompts import (
    A_CLINICAL_TASK,
    ANSWER_VERIFIER_AUDIT,
    B_CONTEXT_SCAN,
    B_FINAL_AUDIT,
    DEIDENTIFICATION_NOTE,
    LIVE_B_CLINICAL_CONTEXT,
    RESIDUAL_SWEEP,
    VERIFIER_PERSONA,
)


class EphemeralMemoryStore(JsonlMemoryStore):
    """Memory that lives only for one request. Clinical runs never write patient content to disk."""

    def __init__(self) -> None:  # noqa: D107 - deliberately skips the file-backed init
        self.path = type("_NoPath", (), {"name": "ephemeral", "stem": "ephemeral", "suffix": ""})()
        self.corrupt_lines = 0
        self._rows: list[MemoryEntry] = []

    def _entries(self) -> list[MemoryEntry]:
        return list(self._rows)

    def record(self, text: str, pinned: bool = False) -> None:
        if (text or "").strip():
            self._rows.append(MemoryEntry(time.time(), text.strip(), pinned))


@dataclass
class ClinicalRequest:
    question: str
    record: dict[str, Any] | str
    index_date: date | None = None


@dataclass
class DisplayFinding:
    kind: str
    severity: str
    statement: str
    evidence: list[str]
    quote: str
    recommended_check: str
    grounded: bool
    grounding_note: str


@dataclass
class ClinicalResult:
    release: Release
    answer: str  # rehydrated, for the clinician's screen only
    decision: GateDecision
    interrupting: list[DisplayFinding]
    advisories: list[DisplayFinding]
    verdict: Verdict | None
    context_summary: str
    receipt: PrivacyReceipt
    supervision: str
    # De-identified artefacts, safe to log or score.
    answer_deidentified: str = ""
    findings_deidentified: list[dict] = field(default_factory=list)
    scan_deidentified: list[dict] = field(default_factory=list)
    fact_paths: dict[str, str] = field(default_factory=dict)
    knowledge_ids: list[str] = field(default_factory=list)
    malformed_items: int = 0
    timings_ms: dict[str, int] = field(default_factory=dict)
    logical_model_calls: int = 0

    def visible_text(self) -> str:
        banner = {
            Release.RELEASE: "RELEASED: no safety findings",
            Release.RELEASE_WITH_ADVISORIES: "RELEASED WITH ADVISORIES",
            Release.HOLD_FOR_CLINICIAN: "HOLD: clinician review required before acting",
            Release.UNVERIFIED: "UNVERIFIED: supervisory check did not complete",
            Release.UNSUPERVISED: "UNSUPERVISED BASELINE",
            Release.BLOCKED: "BLOCKED BY PRIVACY GUARD",
        }[self.release]
        out = [f"=== Dual-Lobe clinical safety: {banner} ==="]
        for r in self.decision.reasons:
            out.append(f"- {r}")

        def block(title: str, items: list[DisplayFinding]) -> None:
            if not items:
                return
            out.append("")
            out.append(title)
            for i, f in enumerate(items, 1):
                tag = "" if f.grounded else f"  (not evidence-grounded: {f.grounding_note})"
                out.append(f"{i}. [{f.severity.upper()}] {f.kind.replace('_', ' ')}: {f.statement}{tag}")
                for ev in f.evidence:
                    out.append(f"     evidence {ev}")
                if f.quote:
                    out.append(f'     quote: "{f.quote}"')
                if f.recommended_check:
                    out.append(f"     check: {f.recommended_check}")

        block("REVIEW BEFORE ACTING:", self.interrupting)
        if self.release != Release.BLOCKED:
            out.append("")
            out.append("--- Answer (Lobe A, unchanged by the supervisor) ---")
            out.append(self.answer.rstrip() or "(no answer)")
        block("ADVISORIES:", self.advisories)
        if self.verdict is not None:
            out.append("")
            out.append(f"Supervisor verdict: [{self.verdict.deception_level}] {self.verdict.rationale}")
        out.append(f"Privacy: {self.receipt.summary()}")
        return "\n".join(out)


# ---------------------------------------------------------------------------
# Output coercion: tolerate formatting noise, never invent content.
# ---------------------------------------------------------------------------

_KINDS = {"unasked_hazard", "missing_information", "answer_error", "unsupported_claim"}
_SEVERITIES = {"critical", "major", "minor"}


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [x for x in re.split(r"[,\s;]+", value) if x]
    if isinstance(value, list):
        return [str(x) for x in value if str(x).strip()]
    return [str(value)]


def _coerce_findings(items: Any) -> tuple[list[ClinicalFinding], int]:
    out: list[ClinicalFinding] = []
    malformed = 0
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            malformed += 1
            continue
        kind = re.sub(r"[\s-]+", "_", str(item.get("kind", "")).strip().lower())
        severity = str(item.get("severity", "")).strip().lower()
        statement = str(item.get("statement", "")).strip()
        if kind not in _KINDS or severity not in _SEVERITIES or not statement:
            malformed += 1
            continue
        out.append(
            ClinicalFinding(
                kind=kind,
                severity=severity,
                statement=statement,
                patient_evidence=_as_list(item.get("patient_evidence")),
                quote=str(item.get("quote") or ""),
                knowledge_evidence=_as_list(item.get("knowledge_evidence")),
                recommended_check=str(item.get("recommended_check") or ""),
            )
        )
    return out, malformed


def parse_scan(raw: str) -> tuple[ContextScan | None, int]:
    data = extract_json_object(raw)
    if not data or "hazards" not in data:
        return None, 0
    hazards, malformed = _coerce_findings(data.get("hazards"))
    return ContextScan(context_summary=str(data.get("context_summary") or ""), hazards=hazards), malformed


def parse_review(raw: str) -> tuple[ClinicalReview | None, int]:
    data = extract_json_object(raw)
    if not data or not isinstance(data.get("answer_verdict"), dict):
        return None, 0
    v = dict(data["answer_verdict"])
    v["deception_level"] = str(v.get("deception_level", "")).strip().upper()
    try:
        verdict = Verdict.model_validate(v)
    except Exception:
        return None, 0
    findings, malformed = _coerce_findings(data.get("findings"))
    return ClinicalReview(answer_verdict=verdict, findings=findings, context_summary=str(data.get("context_summary") or "")), malformed


def _parse_sweep(raw: str) -> ResidualSweep | None:
    data = extract_json_object(raw)
    if not data or not isinstance(data.get("identifiers"), list):
        return None
    try:
        return ResidualSweep.model_validate(data)
    except Exception:
        return None


def _dump(items: list[BaseModel]) -> list[dict]:
    return [x.model_dump() for x in items]


class ClinicalDualLobeEngine:
    name = "dual-lobe-clinical"

    def __init__(
        self,
        *,
        supervision: Supervision = "dual_lobe",
        live_b: bool | None = None,
        knowledge: KnowledgeSource | None = None,
        residual_sweep: bool = True,
        locality: str | None = None,
    ) -> None:
        self.supervision = supervision
        if live_b is None:
            live_b = os.getenv("DUAL_LOBE_CLINICAL_LIVE_B", "true").lower() in {"1", "true", "yes", "on"}
        self.live_b = live_b and supervision == "dual_lobe"
        self.knowledge = knowledge if knowledge is not None else knowledge_from_env()
        self.residual_sweep = residual_sweep
        self.locality = locality or locality_mode()
        # CrewAI telemetry must never be a side channel in clinical mode.
        os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
        os.environ.setdefault("OTEL_SDK_DISABLED", "true")
        egress.install()

    # -- model calls -----------------------------------------------------------

    async def _call_b(self, agent, prompt: str, expected: str, b_specs) -> str:
        try:
            return str(await run_one(agent, prompt, expected, role_key="B_VERIFY", specs=b_specs) or "")
        except Exception as exc:
            return f"B_CALL_FAILED: {type(exc).__name__}"

    async def _residual_sweep(self, session: PrivacySession, view: ClinicalView, b_specs) -> ClinicalView:
        text = view.all_text()
        raw = await self._call_b(
            make_b_adversary(tools=None),
            RESIDUAL_SWEEP.format(text=text),
            "Strict JSON list of remaining identifiers.",
            b_specs,
        )
        sweep = _parse_sweep(raw)
        if sweep is None:
            session.residual_sweep = "failed (unparsable output)"
            return view
        tokens = set(find_tokens(text))
        accepted = []
        for item in sweep.identifiers:
            t = item.text.strip()
            # Only exact strings present in the outbound text are accepted, so a
            # hallucinated "identifier" can never alter clinical content.
            if len(t) >= 2 and t in text and t not in tokens and not find_tokens(t):
                accepted.append((t, item.category))
        added = session.register_residual(accepted)
        session.residual_sweep = "performed"
        session.audit("residual_sweep", detail=f"proposed={len(sweep.identifiers)} accepted={added}")
        return session.reapply(view) if added else view

    def _scan_prompt(self, view: ClinicalView, evidence: dict[str, Snippet]) -> str:
        return B_CONTEXT_SCAN.format(
            deid=DEIDENTIFICATION_NOTE, question=view.question, facts=view.render_facts(), knowledge=render_knowledge(evidence)
        )

    async def _context_scan(self, view, evidence, b_specs) -> tuple[ContextScan | None, int]:
        raw = await self._call_b(
            make_b_adversary(tools=None), self._scan_prompt(view, evidence), "Strict JSON context scan.", b_specs
        )
        return parse_scan(raw)

    async def _final_review(self, view, evidence, answer, scan, b_specs) -> tuple[ClinicalReview | None, int]:
        common = dict(
            deid=DEIDENTIFICATION_NOTE,
            question=view.question,
            facts=view.render_facts(),
            knowledge=render_knowledge(evidence),
            answer=answer,
        )
        if self.supervision == "answer_verifier":
            agent = Agent(
                role="Clinical Answer Verifier",
                goal="Check the answer against the patient record.",
                backstory=VERIFIER_PERSONA,
                llm=make_llm("B_VERIFY"),
                verbose=False,
                allow_delegation=False,
            )
            prompt = ANSWER_VERIFIER_AUDIT.format(**common)
        else:
            agent = make_b_adversary(tools=None)
            scan_text = (
                json.dumps({"context_summary": scan.context_summary, "hazards": _dump(scan.hazards)}, indent=1, ensure_ascii=False)
                if scan is not None
                else "(the independent scan failed; perform the full record scan now as part of this audit)"
            )
            prompt = B_FINAL_AUDIT.format(**common, scan=scan_text, verification_protocol=VERIFICATION_PROTOCOL)
        raw = await self._call_b(agent, prompt, "Strict JSON clinical audit.", b_specs)
        return parse_review(raw)

    # -- main entry --------------------------------------------------------------

    async def run(self, request: ClinicalRequest) -> ClinicalResult:
        t0 = time.perf_counter()
        timings: dict[str, int] = {}
        session = PrivacySession(index_date=request.index_date)
        supervision = self.supervision
        b_specs = None
        b_local = False
        if supervision != "none":
            try:
                b_specs, b_local = resolve_b_specs(self.locality)
            except LocalityError as exc:
                receipt = session.destroy()
                decision = GateDecision(Release.BLOCKED, [str(exc)])
                return ClinicalResult(Release.BLOCKED, "", decision, [], [], None, "", receipt, supervision)
        session.b_locality = "not used" if b_specs is None else ("local" if b_local else "NOT local (development mode)")

        EGRESS_MONITOR.register(session)
        calls = 0
        malformed = 0
        try:
            view = session.build_view(request.question, request.record)
            if supervision == "none" or not self.residual_sweep:
                session.residual_sweep = "disabled"
            elif not b_local:
                session.residual_sweep = "skipped (B is not local)"
            else:
                s0 = time.perf_counter()
                view = await self._residual_sweep(session, view, b_specs)
                calls += 1
                timings["residual_sweep_ms"] = int((time.perf_counter() - s0) * 1000)

            evidence = retrieve_for_view(self.knowledge, [view.question] + [t for _, _, t in view.facts])
            task_text = A_CLINICAL_TASK.format(deid=DEIDENTIFICATION_NOTE, question=view.question, facts=view.render_facts())

            inner = DualLobeEngine(memory=EphemeralMemoryStore(), b_memory=EphemeralMemoryStore())
            trace = ProxyToolTrace()
            delegate_state = DelegateRunState()
            live_state = LiveBState() if self.live_b else None
            monitor = (
                LiveBMonitor(
                    task=task_text,
                    b_memory=inner.b_memory,
                    trace=trace,
                    state=live_state,
                    context_block=LIVE_B_CLINICAL_CONTEXT,
                    b_specs=b_specs,
                )
                if live_state is not None
                else None
            )
            live_task = asyncio.create_task(monitor.run()) if monitor else None
            scan_task = (
                asyncio.create_task(self._context_scan(view, evidence, b_specs)) if supervision == "dual_lobe" else None
            )
            scan: ContextScan | None = None
            review: ClinicalReview | None = None
            try:
                a0 = time.perf_counter()
                answer = await inner._run_a(
                    task=task_text,
                    memory_slice="",
                    strategy_memory="",
                    canonical_state="",
                    trace=trace,
                    delegate_state=delegate_state,
                    live_b_state=live_state,
                )
                await collect_all_delegate_results(delegate_state, trace)
                timings["a_ms"] = int((time.perf_counter() - a0) * 1000)
                calls += 1 + delegate_state.child_count
                if monitor:
                    monitor.stop()
                    await live_task
                    calls += monitor.calls
                if scan_task:
                    scan, m = await scan_task
                    malformed += m
                    calls += 1
                    timings["b_scan_done_ms"] = int((time.perf_counter() - t0) * 1000)
                a_failed = answer.startswith("PRIMARY_A_CALL_FAILED")
                if supervision != "none" and not a_failed:
                    r0 = time.perf_counter()
                    review, m = await self._final_review(view, evidence, answer, scan, b_specs)
                    malformed += m
                    calls += 1
                    timings["b_audit_ms"] = int((time.perf_counter() - r0) * 1000)
            finally:
                if monitor:
                    monitor.stop()
                    if live_task and not live_task.done():
                        await live_task
                if scan_task and not scan_task.done():
                    scan_task.cancel()
                delegate_state.close()

            facts = view.fact_map()
            grounded: list[GroundedFinding] = (
                ground_all(review.findings, facts=facts, question=view.question, answer=answer, knowledge_ids=set(evidence))
                if review
                else []
            )
            decision = decide(
                supervision=supervision,
                privacy_blocked=session.outbound_blocked > 0,
                a_failed=a_failed,
                b_completed=review is not None,
                verdict=review.answer_verdict if review else None,
                findings=grounded,
            )
            if malformed:
                decision.reasons.append(f"{malformed} malformed supervisor item(s) were discarded.")

            def display(g: GroundedFinding) -> DisplayFinding:
                f = g.finding
                ev = []
                for ref in f.patient_evidence:
                    r = normalize_ref(ref)
                    if r in facts:
                        ev.append(f"[{r}] {session.rehydrate(facts[r])}")
                    elif r in {"Q", "A"}:
                        ev.append(f"[{r}] {'question' if r == 'Q' else 'answer'}")
                for ref in f.knowledge_evidence:
                    r = normalize_ref(ref)
                    if r in evidence:
                        ev.append(f"[{r}] {evidence[r].source}")
                return DisplayFinding(
                    kind=f.kind,
                    severity=f.severity,
                    statement=session.rehydrate(f.statement),
                    evidence=ev,
                    quote=session.rehydrate(f.quote),
                    recommended_check=session.rehydrate(f.recommended_check),
                    grounded=g.grounded,
                    grounding_note=g.note,
                )

            shown_answer = "" if decision.release == Release.BLOCKED or a_failed else session.rehydrate(answer)
            result_fields = dict(
                release=decision.release,
                answer=shown_answer,
                decision=decision,
                interrupting=[display(g) for g in decision.interrupting],
                advisories=[display(g) for g in decision.advisories],
                verdict=decision.effective_verdict or (review.answer_verdict if review else None),
                context_summary=session.rehydrate((review.context_summary if review else "") or (scan.context_summary if scan else "")),
                supervision=supervision,
                answer_deidentified="" if a_failed else answer,
                findings_deidentified=[
                    {**g.finding.model_dump(), "grounded": g.grounded, "grounding_note": g.note, "interrupting": g.interrupting}
                    for g in grounded
                ],
                scan_deidentified=_dump(scan.hazards) if scan else [],
                fact_paths=view.fact_paths(),
                knowledge_ids=list(evidence),
                malformed_items=malformed,
            )
        finally:
            EGRESS_MONITOR.unregister(session)
            receipt = session.destroy()

        timings["total_ms"] = int((time.perf_counter() - t0) * 1000)
        return ClinicalResult(**result_fields, receipt=receipt, timings_ms=timings, logical_model_calls=calls)
