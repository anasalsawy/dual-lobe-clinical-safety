"""Patient-identity privacy membrane.

A PrivacySession is created for one clinical request and destroyed at the end
of it. It replaces patient identifiers with opaque tokens before any text can
reach a model that is not local, and it is the only place those tokens can be
turned back into identifiers.

Design properties:

* No plaintext identifier index. Identifiers are found again in later text
  by comparing keyed HMACs of normalized word n-grams, and restored from
  AES-256-GCM ciphertext. The session never keeps a readable copy of an
  identifier.
* Tokens are random per session. The same person gets the same token within
  one request, so the model can reason about "the same person", but tokens
  cannot be linked across requests.
* Dates become offsets from the request's index date ("T-14d"), so clinical
  intervals survive while calendar dates do not. Ages over 89 become "90+"
  (HIPAA Safe Harbor, 45 CFR 164.514(b)(2)).
* destroy() zeroes both keys (crypto-shredding). After that, any ciphertext,
  token, audit fingerprint or log line that outlived the request cannot be
  resolved by anyone, including this process.

The limitations are reported in every PrivacyReceipt rather than hidden. Python
cannot guarantee that transient ``str`` objects are wiped from process memory.
Quasi-identifiers in clinical narrative (a rare condition plus an age, for
example) are not removed by this layer. A remote provider's handling of the
de-identified text it does receive is outside the proxy's control.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import threading
import time
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class PrivacyError(RuntimeError):
    pass


class VaultDestroyed(PrivacyError):
    pass


# ---------------------------------------------------------------------------
# Identifier vocabulary (HIPAA Safe Harbor categories, by structured field name)
# ---------------------------------------------------------------------------

_FIELD_CATEGORY: dict[str, str] = {}
for _cat, _keys in {
    "NAME": (
        "name full_name patient_name first_name last_name given_name family_name "
        "middle_name preferred_name maiden_name surname forename"
    ),
    "LOCATION": (
        "address street street_address address_line address_line1 address_line2 "
        "city town county municipality zip zip_code zipcode postal_code postcode"
    ),
    "PHONE": "phone telephone phone_number mobile cell home_phone work_phone fax",
    "EMAIL": "email email_address",
    "ID": (
        "ssn social_security_number mrn medical_record_number patient_id account_number "
        "insurance_id insurance_number member_id policy_number health_plan_id "
        "license_number drivers_license licence_number vehicle_id license_plate "
        "device_id device_serial serial_number nhs_number health_card_number "
        "biometric_id photo photo_url"
    ),
    "URL": "url website ip ip_address",
    "DOB": "dob date_of_birth birth_date birthdate",
}.items():
    for _k in _keys.split():
        _FIELD_CATEGORY[_k] = _cat

# Every leaf under these keys is identifying (e.g. an emergency contact's name
# and phone number).
_IDENTIFYING_CONTAINERS = {
    "emergency_contact", "next_of_kin", "guarantor", "contacts", "contact",
    "identifiers", "address", "insurance",
}

_TITLES = {"mr", "mrs", "ms", "miss", "mx", "dr", "prof", "sir", "dame", "jr", "sr", "ii", "iii"}

_WORD = re.compile(r"[A-Za-z0-9]+(?:[@._+-][A-Za-z0-9]+)*")
_MAX_NGRAM = 12

_MONTHS = {
    m: i
    for i, names in enumerate(
        [
            ("jan", "january"), ("feb", "february"), ("mar", "march"), ("apr", "april"),
            ("may",), ("jun", "june"), ("jul", "july"), ("aug", "august"),
            ("sep", "sept", "september"), ("oct", "october"), ("nov", "november"),
            ("dec", "december"),
        ],
        start=1,
    )
    for m in names
}
_MONTH_RE = r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sept?(?:ember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"

# Pattern detectors run after known-identifier replacement. Each yields
# (category, compiled pattern, group index holding the identifier).
_PATTERNS: tuple[tuple[str, re.Pattern[str], int], ...] = (
    ("EMAIL", re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b"), 0),
    ("URL", re.compile(r"\bhttps?://[^\s\])>]+|\bwww\.[^\s\])>]+", re.I), 0),
    ("URL", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), 0),
    ("ID", re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), 0),
    (
        "PHONE",
        re.compile(r"(?<![\w.])(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}(?![\w.])"),
        0,
    ),
    ("PHONE", re.compile(r"(?<![\w.])\+\d{1,3}(?:[\s.-]?\d{2,4}){2,5}(?![\w.])"), 0),
    (
        "ID",
        re.compile(
            r"\b(?:MRN|medical record(?: number)?|acct|account|member|policy|insurance|SSN|NHS|patient id)"
            r"\s*(?:no\.?|number|#)?\s*[:#]?\s*((?=[A-Z-]*\d)[A-Z0-9][A-Z0-9-]{3,})",
            re.I,
        ),
        1,
    ),
    ("ID", re.compile(r"\b\d{8,}\b"), 0),
    ("LOCATION", re.compile(r"\b[A-Z]{2}\s+(\d{5}(?:-\d{4})?)\b"), 1),
    (
        "NAME",
        re.compile(r"\b(?:Mr|Mrs|Ms|Miss|Mx)\.?\s+([A-Z][a-zA-Z'-]+(?:\s+[A-Z][a-zA-Z'-]+)?)"),
        1,
    ),
    (
        "NAME",
        re.compile(
            r"\b(?i:wife|husband|spouse|partner|daughter|son|mother|father|mom|mum|dad|sister|brother|"
            r"grandson|granddaughter|grandmother|grandfather|grandma|grandpa|aunt|uncle|niece|nephew|"
            r"cousin|friend|neighbou?r|caregiver|carer|fianc[ée]e?|roommate|landlord)"
            r",?\s+(?:named\s+|called\s+)?([A-Z][a-z'-]+(?:\s+[A-Z][a-z'-]+)?)"
        ),
        1,
    ),
)

_NOT_A_NAME = {
    "The", "He", "She", "They", "Who", "Is", "Was", "And", "But", "At", "In", "On", "Has",
    "Had", "Who", "Will", "Would", "Reports", "Says", "States", "Brought", "Called",
}

_DATE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("ymd", re.compile(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b")),
    ("mdy", re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4}|\d{2})\b")),
    ("mdy_text", re.compile(rf"\b({_MONTH_RE})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?,?\s+(\d{{4}})\b", re.I)),
    ("dmy_text", re.compile(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+({_MONTH_RE})\.?,?\s+(\d{{4}})\b", re.I)),
    ("my_text", re.compile(rf"\b({_MONTH_RE})\.?\s+(\d{{4}})\b", re.I)),
)

_AGE_OVER_89 = re.compile(
    r"\b(9\d|1[0-2]\d)(?=\s*-?\s*(?:years?|yrs?|y/?o\b|yo\b)(?:[\s-]*old)?)", re.I
)

_AGE_LABELLED_OVER_89 = re.compile(r"\b(aged?\s*:?\s*)(9\d|1[0-2]\d)\b", re.I)

_TOKEN_RE = re.compile(r"\[(?:[A-Z]+#[0-9a-f]{6}|DATE [^\]#\s]+#[0-9a-f]{4})\]")


def _norm_words(text: str) -> list[tuple[int, int, str]]:
    return [(m.start(), m.end(), m.group(0).casefold()) for m in _WORD.finditer(text)]


def _normalize_value(text: str) -> str:
    return " ".join(w for _, _, w in _norm_words(text))


def _field_key(key: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(key).strip().lower()).strip("_")


def _month(name: str) -> int:
    name = name.lower().rstrip(".")
    return _MONTHS.get(name) or _MONTHS[name[:3]]


def _parse_date(kind: str, groups: tuple[str, ...]) -> date | None:
    try:
        if kind == "ymd":
            y, m, d = (int(g) for g in groups)
        elif kind == "mdy":
            a, b, y = int(groups[0]), int(groups[1]), int(groups[2])
            if y < 100:
                y += 2000 if y < 50 else 1900
            m, d = (a, b) if a <= 12 else (b, a)
        elif kind == "mdy_text":
            m, d, y = _month(groups[0]), int(groups[1]), int(groups[2])
        elif kind == "dmy_text":
            d, m, y = int(groups[0]), _month(groups[1]), int(groups[2])
        elif kind == "my_text":
            m, y, d = _month(groups[0]), int(groups[1]), 1
        else:
            return None
        return date(y, m, d)
    except (KeyError, ValueError):
        return None


def age_on(birth: date, index: date) -> int:
    return index.year - birth.year - ((index.month, index.day) < (birth.month, birth.day))


def _parse_any_date(value: str) -> date | None:
    for kind, pattern in _DATE_PATTERNS:
        m = pattern.search(value)
        if m:
            return _parse_date(kind, m.groups())
    try:
        return datetime.fromisoformat(value.strip()).date()
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Vault
# ---------------------------------------------------------------------------


class PrivacyVault:
    """Run-scoped token vault: HMAC lookup index + AES-256-GCM ciphertext."""

    def __init__(self) -> None:
        self._enc_key = bytearray(AESGCM.generate_key(bit_length=256))
        self._mac_key = bytearray(secrets.token_bytes(32))
        # hmac(normalized value) -> (token, requires_capitalized_match)
        self._index: dict[bytes, tuple[str, bool]] = {}
        # token -> (nonce, ciphertext)
        self._cipher: dict[str, tuple[bytes, bytes]] = {}
        self._max_words = 1
        self.destroyed = False

    def _check(self) -> None:
        if self.destroyed:
            raise VaultDestroyed("privacy vault has been destroyed")

    def mac(self, normalized: str) -> bytes:
        self._check()
        return hmac.new(bytes(self._mac_key), normalized.encode("utf-8"), hashlib.sha256).digest()

    def fingerprint(self, text: str) -> str:
        """Keyed fingerprint for audit logs; unlinkable once the vault is destroyed."""
        return self.mac("FP\x00" + text).hex()[:32]

    def _encrypt(self, token: str, raw: str) -> None:
        nonce = secrets.token_bytes(12)
        ct = AESGCM(bytes(self._enc_key)).encrypt(nonce, raw.encode("utf-8"), token.encode("utf-8"))
        self._cipher[token] = (nonce, ct)

    def token_for(self, raw: str, category: str, *, label: str = "") -> str:
        """Return the session token for ``raw``, creating and encrypting it if new."""
        self._check()
        normalized = _normalize_value(raw) or raw.strip().casefold()
        key = self.mac(category + "\x00" + normalized) if category == "DATE" else self.mac(normalized)
        hit = self._index.get(key)
        if hit:
            return hit[0]
        if category == "DATE":
            token = f"[DATE {label or 'T?'}#{secrets.token_hex(2)}]"
        else:
            token = f"[{category}#{secrets.token_hex(3)}]"
        self._encrypt(token, raw)
        self._index[key] = (token, False)
        if category != "DATE":
            self._max_words = min(_MAX_NGRAM, max(self._max_words, len(normalized.split())))
        return token

    def add_alias(self, raw_part: str, token: str, *, requires_capital: bool) -> None:
        """Index a partial form (e.g. a surname) so it maps to an existing token."""
        self._check()
        normalized = _normalize_value(raw_part)
        if not normalized:
            return
        key = self.mac(normalized)
        if key not in self._index:
            self._index[key] = (token, requires_capital)
            self._max_words = min(_MAX_NGRAM, max(self._max_words, len(normalized.split())))

    def replace_known(self, text: str) -> tuple[str, int]:
        """Replace every indexed identifier in ``text`` (longest match first)."""
        self._check()
        words = _norm_words(text)
        if not words or not self._index:
            return text, 0
        out: list[str] = []
        cursor = 0
        i = 0
        hits = 0
        while i < len(words):
            matched = False
            for n in range(min(self._max_words, len(words) - i), 0, -1):
                key = self.mac(" ".join(w for _, _, w in words[i : i + n]))
                entry = self._index.get(key)
                if entry is None:
                    continue
                token, requires_capital = entry
                start, end = words[i][0], words[i + n - 1][1]
                if requires_capital and not text[start].isupper():
                    continue
                gap = text[cursor:start]
                if out and out[-1] == token and not gap.strip(" ."):
                    # "Walter Hargrove" -> one token, not two adjacent copies.
                    cursor = end
                    i += n
                    matched = True
                    break
                out.append(gap)
                out.append(token)
                cursor = end
                i += n
                hits += 1
                matched = True
                break
            if not matched:
                i += 1
        out.append(text[cursor:])
        return "".join(out), hits

    def resolve(self, token: str) -> str:
        self._check()
        nonce, ct = self._cipher[token]
        return AESGCM(bytes(self._enc_key)).decrypt(nonce, ct, token.encode("utf-8")).decode("utf-8")

    def rehydrate(self, text: str) -> str:
        self._check()

        def sub(m: re.Match[str]) -> str:
            tok = m.group(0)
            return self.resolve(tok) if tok in self._cipher else tok

        return _TOKEN_RE.sub(sub, text)

    @property
    def token_count(self) -> int:
        return len(self._cipher)

    def destroy(self) -> None:
        if self.destroyed:
            return
        for buf in (self._enc_key, self._mac_key):
            for i in range(len(buf)):
                buf[i] = 0
            buf.clear()
        self._index.clear()
        self._cipher.clear()
        self.destroyed = True


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------


@dataclass
class ClinicalView:
    """De-identified view of one request: the only patient data A may see."""

    question: str
    facts: list[tuple[str, str, str]]  # (fact_id, path, text)

    def fact_map(self) -> dict[str, str]:
        return {fid: f"{path}: {text}" for fid, path, text in self.facts}

    def fact_paths(self) -> dict[str, str]:
        return {fid: path for fid, path, _ in self.facts}

    def render_facts(self) -> str:
        return "\n".join(f"[{fid}] {path}: {text}" for fid, path, text in self.facts) or "(no record content)"

    def all_text(self) -> str:
        return self.question + "\n" + self.render_facts()


@dataclass
class AuditEvent:
    ts: float
    event: str
    destination: str = ""
    fingerprint: str = ""
    detail: str = ""


@dataclass(frozen=True)
class PrivacyReceipt:
    session_id: str
    identifiers_protected: dict[str, int]
    detection_sources: dict[str, int]
    outbound_checked: int
    outbound_to_remote: int
    outbound_to_local: int
    outbound_sanitized_at_egress: int
    outbound_blocked: int
    b_locality: str
    residual_sweep: str
    key_destroyed: bool
    destroyed_at: float | None
    audit_log: tuple[AuditEvent, ...]
    limitations: tuple[str, ...]

    def summary(self) -> str:
        total = sum(self.identifiers_protected.values())
        return (
            f"{total} identifier(s) pseudonymized; {self.outbound_to_remote} remote call(s) checked, "
            f"{self.outbound_sanitized_at_egress} sanitized at egress, {self.outbound_blocked} blocked; "
            f"B locality: {self.b_locality}; residual sweep: {self.residual_sweep}; "
            f"session key destroyed: {'yes' if self.key_destroyed else 'NO'}."
        )


class PrivacySession:
    def __init__(self, *, index_date: date | None = None) -> None:
        self.session_id = secrets.token_hex(8)
        self.index_date = index_date or date.today()
        self.vault = PrivacyVault()
        self._lock = threading.RLock()
        self._counts: dict[str, int] = {}
        self._sources: dict[str, int] = {}
        self._audit: list[AuditEvent] = []
        self.outbound_checked = 0
        self.outbound_remote = 0
        self.outbound_local = 0
        self.outbound_sanitized = 0
        self.outbound_blocked = 0
        self.b_locality = "not used"
        self.residual_sweep = "not run"
        self._destroyed_at: float | None = None

    # -- bookkeeping ---------------------------------------------------------

    def _note(self, category: str, source: str, n: int = 1) -> None:
        self._counts[category] = self._counts.get(category, 0) + n
        self._sources[source] = self._sources.get(source, 0) + n

    def audit(self, event: str, *, destination: str = "", text: str = "", detail: str = "") -> None:
        with self._lock:
            fp = self.vault.fingerprint(text) if text and not self.vault.destroyed else ""
            self._audit.append(AuditEvent(time.time(), event, destination, fp, detail))

    @property
    def destroyed(self) -> bool:
        return self.vault.destroyed

    # -- registration --------------------------------------------------------

    def _register(self, raw: str, category: str, source: str) -> str:
        raw = str(raw).strip()
        if not raw:
            return ""
        before = self.vault.token_count
        token = self.vault.token_for(raw, category)
        if self.vault.token_count > before:
            self._note(category, source)
        if category == "NAME":
            parts = [w for w in _WORD.findall(raw) if w.casefold() not in _TITLES and len(w) >= 2]
            if len(parts) > 1:
                for part in parts:
                    self.vault.add_alias(part, token, requires_capital=True)
        return token

    def _register_structured(self, value: Any, category: str) -> None:
        if isinstance(value, dict):
            for k, v in value.items():
                self._register_structured(v, _FIELD_CATEGORY.get(_field_key(k), category))
        elif isinstance(value, list):
            for v in value:
                self._register_structured(v, category)
        elif value not in (None, ""):
            self._register(str(value), category, "structured_field")

    def register_residual(self, values: list[tuple[str, str]], *, source: str = "local_b_sweep") -> int:
        """Register identifiers found by the local B sweep. Returns count added."""
        added = 0
        with self._lock:
            for raw, category in values:
                category = re.sub(r"[^A-Z]", "", str(category).upper())[:12] or "OTHER"
                before = self.vault.token_count
                self._register(raw, category, source)
                added += self.vault.token_count - before
        return added

    # -- de-identification ---------------------------------------------------

    def _date_token(self, raw: str, parsed: date | None, month_only: bool) -> str:
        if parsed is None:
            label = "T?"
        elif month_only:
            months = (parsed.year - self.index_date.year) * 12 + parsed.month - self.index_date.month
            label = f"T{months:+d}mo"
        else:
            days = (parsed - self.index_date).days
            label = f"T{days:+d}d"
        return self.vault.token_for(raw, "DATE", label=label)

    def pseudonymize_text(self, text: str, *, source_prefix: str = "") -> str:
        with self._lock:
            out, known = self.vault.replace_known(str(text))
            if known:
                self._sources[source_prefix + "known_identifier_propagation"] = (
                    self._sources.get(source_prefix + "known_identifier_propagation", 0) + known
                )
            for category, pattern, group in _PATTERNS:
                def repl(m: re.Match[str], category=category, group=group) -> str:
                    raw = m.group(group)
                    if category == "NAME" and raw.split()[0] in _NOT_A_NAME:
                        return m.group(0)
                    token = self._register(raw, category, source_prefix + "pattern")
                    if group == 0:
                        return token
                    return m.group(0)[: m.start(group) - m.start(0)] + token + m.group(0)[m.end(group) - m.start(0):]

                out = pattern.sub(repl, out)
            # Names found by patterns may recur without their title/relation cue.
            out, _ = self.vault.replace_known(out)
            for kind, pattern in _DATE_PATTERNS:
                def drepl(m: re.Match[str], kind=kind) -> str:
                    before = self.vault.token_count
                    token = self._date_token(m.group(0), _parse_date(kind, m.groups()), kind == "my_text")
                    if self.vault.token_count > before:
                        self._note("DATE", source_prefix + "date_pattern")
                    return token

                out = pattern.sub(drepl, out)
            out, n_age = _AGE_OVER_89.subn("90+", out)
            out, n_age2 = _AGE_LABELLED_OVER_89.subn(lambda m: m.group(1) + "90+", out)
            n_age += n_age2
            if n_age:
                self._note("AGE_OVER_89", source_prefix + "age_generalization", n_age)
            return out

    def build_view(self, question: str, record: Any) -> ClinicalView:
        """Register structured identifiers, then emit the de-identified view.

        Identifier fields are removed from the view entirely (minimum
        necessary); a date of birth is replaced by ``age_years``.
        """
        with self._lock:
            derived: list[tuple[str, str]] = []

            def collect(value: Any, path: str) -> None:
                if isinstance(value, dict):
                    for k, v in value.items():
                        key = _field_key(k)
                        sub = f"{path}.{k}" if path else str(k)
                        category = _FIELD_CATEGORY.get(key)
                        if category == "DOB":
                            self._register(str(v), "DOB", "structured_field")
                            birth = _parse_any_date(str(v))
                            if birth:
                                age = age_on(birth, self.index_date)
                                derived.append(("age_years", "90+" if age > 89 else str(age)))
                        elif category or key in _IDENTIFYING_CONTAINERS:
                            self._register_structured(v, category or "OTHER")
                        else:
                            collect(v, sub)
                elif isinstance(value, list):
                    for i, v in enumerate(value):
                        collect(v, f"{path}[{i}]")

            collect(record, "")

            facts: list[tuple[str, str, str]] = []

            def add(path: str, text: str) -> None:
                facts.append((f"F{len(facts) + 1}", path or "record", text))

            for path, text in derived:
                add(path, text)

            def emit(value: Any, path: str) -> None:
                if isinstance(value, dict):
                    for k, v in value.items():
                        key = _field_key(k)
                        if key in _FIELD_CATEGORY or key in _IDENTIFYING_CONTAINERS:
                            continue
                        sub = f"{path}.{k}" if path else str(k)
                        if key in {"age", "age_years"} and str(v).strip().isdigit() and int(str(v).strip()) > 89:
                            self._note("AGE_OVER_89", "age_generalization")
                            add(sub, "90+")
                            continue
                        emit(v, sub)
                elif isinstance(value, list):
                    for i, v in enumerate(value):
                        emit(v, f"{path}[{i}]")
                elif value is None or value == "":
                    return
                elif isinstance(value, str) and "\n" in value.strip():
                    lines = [ln.strip() for ln in value.splitlines() if ln.strip()]
                    for n, line in enumerate(lines, 1):
                        add(f"{path}#L{n}", self.pseudonymize_text(line))
                else:
                    add(path, self.pseudonymize_text(str(value)))

            emit(record if not isinstance(record, str) else {"note": record}, "")
            return ClinicalView(question=self.pseudonymize_text(question), facts=facts)

    def reapply(self, view: ClinicalView) -> ClinicalView:
        """Re-run de-identification over an existing view (after new registrations)."""
        return ClinicalView(
            question=self.pseudonymize_text(view.question),
            facts=[(fid, path, self.pseudonymize_text(text)) for fid, path, text in view.facts],
        )

    # -- egress ---------------------------------------------------------------

    def sanitize_outbound(self, text: str, *, destination: str) -> str:
        """De-identify text bound for a non-local destination; audit the check."""
        with self._lock:
            self.outbound_checked += 1
            self.outbound_remote += 1
            cleaned = self.pseudonymize_text(text, source_prefix="egress_")
            if cleaned != text:
                self.outbound_sanitized += 1
                self.audit("egress_sanitized", destination=destination, text=cleaned)
            else:
                self.audit("egress_clean", destination=destination, text=cleaned)
            return cleaned

    def note_local(self, text: str, *, destination: str) -> None:
        with self._lock:
            self.outbound_checked += 1
            self.outbound_local += 1
            self.audit("local_call", destination=destination, text=text)

    def note_blocked(self, *, destination: str, reason: str) -> None:
        with self._lock:
            self.outbound_blocked += 1
            self.audit("egress_blocked", destination=destination, detail=reason)

    # -- output ---------------------------------------------------------------

    def rehydrate(self, text: str) -> str:
        return self.vault.rehydrate(text)

    def destroy(self) -> PrivacyReceipt:
        with self._lock:
            if not self.vault.destroyed:
                self.audit("session_destroyed")
                self.vault.destroy()
                self._destroyed_at = time.time()
            limitations = [
                "Key destruction overwrites the session's key buffers; Python cannot guarantee that "
                "transient string copies are wiped from process memory before garbage collection.",
                "Quasi-identifiers inside clinical narrative (e.g. rare condition + age + occupation) "
                "are not removed by deterministic de-identification.",
                "Remote providers receive de-identified text only; their retention of that text is "
                "governed by the provider agreement, not by this proxy.",
            ]
            if self.residual_sweep != "performed":
                limitations.append(
                    "The local-B residual identifier sweep was not performed for this request; free-text "
                    "identifiers without a structural cue (e.g. a bare first name or a town) may remain."
                )
            return PrivacyReceipt(
                session_id=self.session_id,
                identifiers_protected=dict(self._counts),
                detection_sources=dict(self._sources),
                outbound_checked=self.outbound_checked,
                outbound_to_remote=self.outbound_remote,
                outbound_to_local=self.outbound_local,
                outbound_sanitized_at_egress=self.outbound_sanitized,
                outbound_blocked=self.outbound_blocked,
                b_locality=self.b_locality,
                residual_sweep=self.residual_sweep,
                key_destroyed=self.vault.destroyed,
                destroyed_at=self._destroyed_at,
                audit_log=tuple(self._audit),
                limitations=tuple(limitations),
            )


def find_tokens(text: str) -> list[str]:
    return _TOKEN_RE.findall(text)
