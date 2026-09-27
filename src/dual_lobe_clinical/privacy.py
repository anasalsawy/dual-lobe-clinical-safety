from __future__ import annotations

import gc
import hashlib
import hmac
import json
import os
import re
import secrets
from dataclasses import dataclass
from enum import Enum
from typing import Any


class PrivacyDecision(str, Enum):
    ALLOW = "allow"
    SANITIZE = "sanitize"
    BLOCK = "block"


class PrivacyAssurance(str, Enum):
    PROXY_MINIMIZED = "proxy_minimized"
    PROVIDER_ATTESTED = "provider_attested"
    LOCAL_ISOLATED = "local_isolated"
    UNVERIFIED_REMOTE = "unverified_remote"


_DIRECT_KEYS = {
    "name", "full_name", "patient_name", "first_name", "last_name",
    "address", "street_address", "email", "phone", "telephone",
    "ssn", "social_security_number", "mrn", "medical_record_number",
    "account_number", "member_id", "insurance_id", "license_number",
    "device_id", "ip_address", "url", "biometric_id", "photo",
    "date_of_birth", "dob",
}

_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("email", re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)),
    ("phone", re.compile(r"(?<!\d)(?:\+?\d[\d .()\-]{7,}\d)(?!\d)")),
    ("ssn", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("ipv4", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")),
)


@dataclass(frozen=True)
class ProviderPrivacyPolicy:
    provider_name: str = "unspecified"
    allow_identifiable_phi: bool = False
    no_training_attested: bool = False
    zero_retention_attested: bool = False
    business_associate_or_equivalent: bool = False
    local_inference: bool = False

    @property
    def assurance(self) -> PrivacyAssurance:
        if self.local_inference:
            return PrivacyAssurance.LOCAL_ISOLATED
        if (
            self.no_training_attested
            and self.zero_retention_attested
            and self.business_associate_or_equivalent
        ):
            return PrivacyAssurance.PROVIDER_ATTESTED
        return PrivacyAssurance.UNVERIFIED_REMOTE


@dataclass(frozen=True)
class PrivacyReceipt:
    decision: PrivacyDecision
    assurance: PrivacyAssurance
    direct_identifier_types: tuple[str, ...]
    raw_phi_forwarded: bool
    persisted_raw_locally: bool
    sanitized_query_fingerprint: str
    sanitized_context_fingerprint: str
    provider_name: str
    provider_zero_retention_attested: bool
    provider_no_training_attested: bool
    provider_business_associate_or_equivalent: bool
    local_discard_status: str
    limitations: tuple[str, ...] = ()


class PrivacyGuard:
    """Deterministic pre-inference privacy membrane.

    This is intentionally not an LLM. It executes before A or B receives input.
    It minimizes direct identifiers, emits only sanitized payloads to inference,
    and produces an audit receipt without persisting raw input.

    This is NOT a certification of HIPAA de-identification and cannot prove a
    remote provider physically erased every internal copy. Those claims require
    external contractual/technical attestation.
    """

    def __init__(
        self,
        provider_policy: ProviderPrivacyPolicy | None = None,
        *,
        audit_key: bytes | None = None,
    ) -> None:
        self.provider_policy = provider_policy or ProviderPrivacyPolicy()
        configured = os.getenv("DUAL_LOBE_PRIVACY_AUDIT_KEY")
        self._audit_key = audit_key or (
            configured.encode("utf-8") if configured else secrets.token_bytes(32)
        )

    def _fingerprint(self, text: str) -> str:
        return hmac.new(
            self._audit_key,
            text.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    @staticmethod
    def _token(label: str) -> str:
        return f"<REDACTED:{label.upper()}>"

    def _sanitize_object(self, value: Any, found: set[str]) -> Any:
        if isinstance(value, dict):
            out = {}
            for key, item in value.items():
                normalized = str(key).strip().lower()
                if normalized in _DIRECT_KEYS:
                    found.add(normalized)
                    out[key] = self._token(normalized)
                else:
                    out[key] = self._sanitize_object(item, found)
            return out
        if isinstance(value, list):
            return [self._sanitize_object(x, found) for x in value]
        if isinstance(value, str):
            return self._sanitize_text(value, found)
        return value

    def _sanitize_text(self, text: str, found: set[str]) -> str:
        out = text
        for label, pattern in _PATTERNS:
            if pattern.search(out):
                found.add(label)
                out = pattern.sub(self._token(label), out)
        return out

    def sanitize(self, text: str) -> tuple[str, tuple[str, ...]]:
        found: set[str] = set()
        try:
            parsed = json.loads(text)
        except Exception:
            sanitized = self._sanitize_text(text, found)
        else:
            sanitized_obj = self._sanitize_object(parsed, found)
            sanitized = json.dumps(sanitized_obj, ensure_ascii=False, sort_keys=True)
        return sanitized, tuple(sorted(found))

    def prepare(
        self,
        *,
        query: str,
        patient_context: str,
    ) -> tuple[str, str, PrivacyReceipt]:
        sanitized_query, q_types = self.sanitize(query)
        sanitized_context, c_types = self.sanitize(patient_context)
        direct_types = tuple(sorted(set(q_types) | set(c_types)))

        raw_forwarded = bool(
            direct_types
            and self.provider_policy.allow_identifiable_phi
            and sanitized_query == query
            and sanitized_context == patient_context
        )

        decision = (
            PrivacyDecision.SANITIZE if direct_types else PrivacyDecision.ALLOW
        )

        limitations = [
            "Proxy does not persist raw query or raw patient context in run results.",
            "Python reference release is not cryptographic memory erasure.",
        ]
        if self.provider_policy.assurance is PrivacyAssurance.UNVERIFIED_REMOTE:
            limitations.append(
                "Remote-provider deletion/training behavior is not independently verified by the proxy."
            )

        receipt = PrivacyReceipt(
            decision=decision,
            assurance=self.provider_policy.assurance,
            direct_identifier_types=direct_types,
            raw_phi_forwarded=raw_forwarded,
            persisted_raw_locally=False,
            sanitized_query_fingerprint=self._fingerprint(sanitized_query),
            sanitized_context_fingerprint=self._fingerprint(sanitized_context),
            provider_name=self.provider_policy.provider_name,
            provider_zero_retention_attested=self.provider_policy.zero_retention_attested,
            provider_no_training_attested=self.provider_policy.no_training_attested,
            provider_business_associate_or_equivalent=self.provider_policy.business_associate_or_equivalent,
            local_discard_status="best_effort_reference_release",
            limitations=tuple(limitations),
        )
        return sanitized_query, sanitized_context, receipt

    def sanitize_trace(self, trace_text: str) -> tuple[str, tuple[str, ...]]:
        return self.sanitize(trace_text)

    @staticmethod
    def discard_best_effort(*objects: Any) -> str:
        # Python strings are immutable and may have copies outside this scope;
        # this releases local references only and deliberately does not claim
        # cryptographic zeroization.
        del objects
        gc.collect()
        return "best_effort_reference_release"
