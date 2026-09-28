"""Where a model runs decides what it may see.

Lobe B is required to run on infrastructure the deploying institution
controls. Locality is judged from the provider spec's destination, never
from the role name:

* loopback hosts (localhost, 127.0.0.0/8, ::1) are local;
* ``ollama/`` and ``ollama_chat/`` models with no base URL are local, unless
  OLLAMA_API_BASE / OLLAMA_HOST points elsewhere;
* any other host is local only if listed in DUAL_LOBE_CLINICAL_LOCAL_HOSTS
  (comma-separated host names), e.g. an in-hospital inference server.

Everything else counts as remote.
"""

from __future__ import annotations

import ipaddress
import os
from urllib.parse import urlparse

from dual_lobe_crewai.llm_factory import resolve_role_specs
from dual_lobe_crewai.provider_control import ProviderSpec


class LocalityError(RuntimeError):
    pass


_LOCAL_PREFIXES = ("ollama/", "ollama_chat/")


def _host(url: str) -> str:
    if "//" not in url:
        url = "http://" + url
    return (urlparse(url).hostname or "").lower()


def _allowlisted_hosts() -> set[str]:
    raw = os.getenv("DUAL_LOBE_CLINICAL_LOCAL_HOSTS", "")
    return {h.strip().lower() for h in raw.split(",") if h.strip()}


def _is_local_host(host: str) -> bool:
    if not host:
        return False
    if host == "localhost" or host in _allowlisted_hosts():
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def is_local_destination(model: str, base_url: str | None) -> bool:
    if base_url:
        return _is_local_host(_host(base_url))
    if model.lower().startswith(_LOCAL_PREFIXES):
        ollama = os.getenv("OLLAMA_API_BASE") or os.getenv("OLLAMA_HOST") or "http://localhost:11434"
        return _is_local_host(_host(ollama))
    return False


def is_local_spec(spec: ProviderSpec) -> bool:
    return is_local_destination(spec.model, spec.base_url)


def destination_label(spec: ProviderSpec) -> str:
    where = "local" if is_local_spec(spec) else "remote"
    return f"{where}:{spec.model}"


def locality_mode() -> str:
    mode = os.getenv("DUAL_LOBE_CLINICAL_B_LOCALITY", "require").strip().lower()
    return mode if mode in {"require", "prefer"} else "require"


def resolve_b_specs(mode: str | None = None) -> tuple[list[ProviderSpec], bool]:
    """Return B's provider candidates and whether they are all local.

    ``require`` (default): only local candidates are kept. Cross-role failover
    to A's remote provider is dropped. If none remain, LocalityError is raised.
    ``prefer`` (development only): local candidates first, then the rest.
    Remote B calls are still de-identified at egress, but the residual
    identifier sweep is skipped and the receipt records the degraded mode.
    """
    mode = mode or locality_mode()
    specs = resolve_role_specs("B_VERIFY")
    local = [s for s in specs if is_local_spec(s)]
    if mode == "require":
        if not local:
            raise LocalityError(
                "Clinical mode requires Lobe B to run on a local model, but no local B provider is "
                "configured. Set DUAL_LOBE_B_MODEL to a local model (e.g. ollama/<model>, or a "
                "hosted_vllm/openai-compatible model with DUAL_LOBE_B_BASE_URL=http://localhost:<port>/v1), "
                "or list your in-house inference host in DUAL_LOBE_CLINICAL_LOCAL_HOSTS."
            )
        return local, True
    remote = [s for s in specs if not is_local_spec(s)]
    return local + remote, bool(local) and not remote
