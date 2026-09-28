"""Scripted stand-in for model providers, installed at the lowest runtime layer.

The fake replaces ``runner._single_call`` and ``runner.make_llm``. Everything
above that, including provider resolution, egress filtering and the rate
controller, runs for real, and every payload that would have left the
process is recorded with its destination.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

import dual_lobe_crewai.runner as runner
from dual_lobe_clinical.locality import is_local_spec


@dataclass
class FakeLLM:
    spec: object


@dataclass
class Sent:
    local: bool
    model: str
    text: str


@dataclass
class FakeProviders:
    sweep: dict | None = None
    scan: dict | None = None
    audit: dict | None = None
    verifier: dict | None = None
    answer: str = "Suggested plan: ibuprofen 400 mg three times daily with food [F2]."
    raw_scan: str | None = None
    raw_audit: str | None = None
    sent: list[Sent] = field(default_factory=list)

    def fact_id(self, prompt: str, path_fragment: str) -> str:
        m = re.search(r"\[(F\d+)\] " + re.escape(path_fragment), prompt)
        return m.group(1) if m else "F999"

    def respond(self, prompt: str) -> str:
        if "local privacy auditor" in prompt:
            return json.dumps(self.sweep or {"identifiers": []})
        if "deliberately NOT been shown A's answer" in prompt:
            if self.raw_scan is not None:
                return self.raw_scan
            return json.dumps(self.scan(prompt) if callable(self.scan) else (self.scan or {"context_summary": "", "hazards": []}))
        if "A has now answered" in prompt:
            if self.raw_audit is not None:
                return self.raw_audit
            return json.dumps(self.audit(prompt) if callable(self.audit) else self.audit)
        if "Verify A's answer" in prompt:
            return json.dumps(self.verifier(prompt) if callable(self.verifier) else self.verifier)
        if "running CONTINUOUSLY" in prompt:
            return json.dumps({"intervene": False, "severity": "info", "message": "", "state_note": "observing"})
        if "answering a licensed clinician" in prompt:
            return self.answer
        return "UNEXPECTED_PROMPT"

    def install(self, monkeypatch) -> None:
        def fake_make_llm(role, spec=None):
            return FakeLLM(spec)

        async def fake_single_call(agent, description, expected_output):
            spec = agent.llm.spec
            self.sent.append(Sent(is_local_spec(spec), spec.model, description + "\n" + expected_output))
            return self.respond(description)

        monkeypatch.setattr(runner, "make_llm", fake_make_llm)
        monkeypatch.setattr(runner, "_single_call", fake_single_call)

    def remote_text(self) -> str:
        return "\n".join(s.text for s in self.sent if not s.local)

    def local_text(self) -> str:
        return "\n".join(s.text for s in self.sent if s.local)


def configure_env(monkeypatch, *, b_model: str = "ollama/llama3.1:8b", b_base: str = "") -> None:
    monkeypatch.setenv("DUAL_LOBE_A_MODEL", "openrouter/vendor/remote-model")
    monkeypatch.setenv("DUAL_LOBE_B_MODEL", b_model)
    if b_base:
        monkeypatch.setenv("DUAL_LOBE_B_BASE_URL", b_base)
    else:
        monkeypatch.delenv("DUAL_LOBE_B_BASE_URL", raising=False)
    for var in ("OPENAI_API_BASE", "DUAL_LOBE_A_BASE_URL", "OLLAMA_API_BASE", "OLLAMA_HOST",
                "DUAL_LOBE_CLINICAL_LOCAL_HOSTS", "DUAL_LOBE_CLINICAL_B_LOCALITY",
                "DUAL_LOBE_CLINICAL_KNOWLEDGE_PATH", "DUAL_LOBE_FALLBACKS",
                "DUAL_LOBE_A_FALLBACKS", "DUAL_LOBE_B_VERIFY_FALLBACKS"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-not-a-real-key")
    monkeypatch.setenv("DUAL_LOBE_RETRY_ROUNDS", "1")
    monkeypatch.setenv("DUAL_LOBE_CLINICAL_LIVE_B", "false")


RECORD = {
    "patient": {
        "name": "Walter J. Hargrove",
        "dob": "1954-03-02",
        "mrn": "MRN-0048213",
        "phone": "(555) 201-3344",
        "address": {"street": "14 Elm Street", "city": "Springfield", "zip": "62704"},
        "emergency_contact": {"name": "Linda Hargrove", "phone": "555-201-9876"},
    },
    "medications": ["lisinopril 20 mg daily", "furosemide 40 mg daily"],
    "labs": {"eGFR": "28 mL/min/1.73m2 on 2026-09-14"},
    "note": (
        "Mr. Hargrove seen 09/20/2026 for right knee osteoarthritis flare. His daughter Priya drove him. "
        "Lives with Tomasz. Recently back from Sedona. Email walt.h@example.com."
    ),
}

RAW_IDENTIFIERS = [
    "Hargrove", "Walter", "MRN-0048213", "0048213", "201-3344", "Elm Street", "Springfield", "62704",
    "Linda", "555-201-9876", "Priya", "Tomasz", "Sedona", "walt.h@example.com", "1954-03-02",
    "2026-09-14", "09/20/2026",
]
