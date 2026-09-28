"""Egress monitor: every outbound model payload passes through here.

The monitor is keyed on destination, not role. While any clinical
PrivacySession is active:

* a payload bound for a local destination is logged and passed unchanged;
* a payload bound for a remote destination is de-identified against every
  active session (known identifiers, patterns, dates, ages) and audited;
* if de-identification itself fails, the call is refused (EgressDenied), so
  the runtime fails closed.

It is installed at two layers. The runtime's own ``run_one`` sees each task
prompt. When the installed CrewAI supports ``before_llm_call`` hooks, the
monitor also sees every message CrewAI sends, including tool results that
enter A's context mid-run.
"""

from __future__ import annotations

import threading

from dual_lobe_crewai.provider_control import ProviderSpec
from dual_lobe_crewai.runner import EgressDenied, register_egress_filter

from .locality import destination_label, is_local_destination, is_local_spec
from .privacy import PrivacySession


class EgressMonitor:
    def __init__(self) -> None:
        self._sessions: list[PrivacySession] = []
        self._lock = threading.Lock()

    def register(self, session: PrivacySession) -> None:
        with self._lock:
            if session not in self._sessions:
                self._sessions.append(session)

    def unregister(self, session: PrivacySession) -> None:
        with self._lock:
            if session in self._sessions:
                self._sessions.remove(session)

    def active(self) -> list[PrivacySession]:
        with self._lock:
            return [s for s in self._sessions if not s.destroyed]

    def filter_text(self, text: str, *, local: bool, destination: str) -> str:
        sessions = self.active()
        if not sessions or not text:
            return text
        if local:
            for s in sessions:
                s.note_local(text, destination=destination)
            return text
        out = text
        for s in sessions:
            try:
                out = s.sanitize_outbound(out, destination=destination)
            except Exception as exc:  # fail closed
                s.note_blocked(destination=destination, reason=type(exc).__name__)
                raise EgressDenied(f"privacy egress check failed for {destination}") from exc
        return out

    # runner.run_one filter
    def __call__(self, spec: ProviderSpec, text: str) -> str:
        return self.filter_text(text, local=is_local_spec(spec), destination=destination_label(spec))

    # CrewAI before_llm_call hook
    def crewai_hook(self, context) -> bool | None:
        if not self.active():
            return None
        llm = getattr(context, "llm", None)
        model = str(getattr(llm, "model", "") or "")
        base_url = getattr(llm, "base_url", None) or getattr(llm, "api_base", None)
        local = is_local_destination(model, base_url)
        destination = f"{'local' if local else 'remote'}:{model}"
        try:
            for message in getattr(context, "messages", None) or []:
                if not isinstance(message, dict):
                    continue
                content = message.get("content")
                if isinstance(content, str):
                    message["content"] = self.filter_text(content, local=local, destination=destination)
                elif isinstance(content, list):
                    for part in content:
                        if isinstance(part, dict) and isinstance(part.get("text"), str):
                            part["text"] = self.filter_text(part["text"], local=local, destination=destination)
        except EgressDenied:
            return False
        return None


EGRESS_MONITOR = EgressMonitor()
_installed = False
_install_lock = threading.Lock()


def install() -> None:
    """Idempotently attach the monitor to the runtime and (if supported) CrewAI."""
    global _installed
    with _install_lock:
        if _installed:
            return
        register_egress_filter(EGRESS_MONITOR)
        try:
            from crewai.hooks.llm_hooks import register_before_llm_call_hook

            register_before_llm_call_hook(EGRESS_MONITOR.crewai_hook)
        except Exception:
            pass
        _installed = True
