"""Deterministic control logic: evidence grounding and the release gate.

Nothing in this module calls a model. The model lobes propose; this module
decides. The rules are specified in docs/METHODS.md and are covered one by
one in tests/test_clinical_control.py.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from dual_lobe_crewai.models import Verdict

from .models import ClinicalFinding, Release, Supervision

_REF = re.compile(r"^\[?\s*([A-Za-z]+)\s*[-:#]?\s*(\d*)\s*\]?$")
_SEVERITY_RANK = {"critical": 3, "major": 2, "minor": 1}
INTERRUPTING = {"critical", "major"}


def _norm(text: str) -> str:
    return " ".join(re.sub(r"[^\w%./+-]+", " ", text.casefold()).split())


def normalize_ref(ref: str) -> str:
    m = _REF.match(str(ref).strip())
    if not m:
        return str(ref).strip()
    letters, digits = m.group(1).upper(), m.group(2)
    return f"{letters}{digits}"


@dataclass
class GroundedFinding:
    finding: ClinicalFinding
    grounded: bool
    note: str = ""

    @property
    def interrupting(self) -> bool:
        return self.grounded and self.finding.severity in INTERRUPTING


def ground_finding(
    finding: ClinicalFinding,
    *,
    facts: dict[str, str],
    question: str,
    answer: str,
    knowledge_ids: set[str],
) -> GroundedFinding:
    """Check that a finding's citations exist and actually support it.

    A finding is grounded only if:
      1. every cited reference exists (F# in the record, Q, A, K# retrieved in this run);
      2. it cites what its kind requires:
         unasked_hazard / answer_error  -> at least one record fact (F#),
         missing_information            -> a record fact or the question (F# / Q),
         unsupported_claim              -> the answer (A);
      3. its quote, if given, appears verbatim (after whitespace/case
         normalization) in one of the cited sources.
    Fabricated references or quotes make a finding ungrounded. That is also
    a deception signal about the supervisor itself.
    """
    sources = {"Q": question, "A": answer, **facts}
    refs = [normalize_ref(r) for r in finding.patient_evidence]
    krefs = [normalize_ref(r) for r in finding.knowledge_evidence]

    unknown = [r for r in refs if r not in sources]
    if unknown:
        return GroundedFinding(finding, False, f"cites evidence that does not exist: {unknown}")
    bad_k = [r for r in krefs if r not in knowledge_ids]
    if bad_k:
        return GroundedFinding(finding, False, f"cites knowledge that was not retrieved: {bad_k}")

    fact_refs = [r for r in refs if r.startswith("F")]
    kind = finding.kind
    if kind in {"unasked_hazard", "answer_error"} and not fact_refs:
        return GroundedFinding(finding, False, "no patient-record fact cited")
    if kind == "missing_information" and not (fact_refs or "Q" in refs):
        return GroundedFinding(finding, False, "does not cite what makes the information necessary")
    if kind == "unsupported_claim" and "A" not in refs:
        return GroundedFinding(finding, False, "does not cite the answer claim")

    quote = _norm(finding.quote.strip().strip('"').strip("'"))
    if quote and not any(quote in _norm(sources[r]) for r in refs):
        return GroundedFinding(finding, False, "quote not found in the cited evidence")
    return GroundedFinding(finding, True, "")


def ground_all(findings: list[ClinicalFinding], **kw) -> list[GroundedFinding]:
    seen: set[tuple] = set()
    out: list[GroundedFinding] = []
    # The same finding reported twice keeps its most severe form.
    for f in sorted(findings, key=lambda x: -_SEVERITY_RANK[x.severity]):
        key = (f.kind, tuple(sorted(normalize_ref(r) for r in f.patient_evidence)), _norm(f.statement))
        if key in seen:
            continue
        seen.add(key)
        out.append(ground_finding(f, **kw))
    out.sort(key=lambda g: (not g.grounded, -_SEVERITY_RANK[g.finding.severity]))
    return out


@dataclass
class GateDecision:
    release: Release
    reasons: list[str] = field(default_factory=list)
    interrupting: list[GroundedFinding] = field(default_factory=list)
    advisories: list[GroundedFinding] = field(default_factory=list)
    effective_verdict: Verdict | None = None

    @property
    def requires_acknowledgement(self) -> bool:
        return self.release in {Release.HOLD_FOR_CLINICIAN, Release.UNVERIFIED}


def effective_verdict(verdict: Verdict, grounded: list[GroundedFinding]) -> tuple[Verdict, list[str]]:
    """Apply the verdict rules that do not depend on the release decision.

    * GREEN is impossible while B itself reports a grounded finding or leaves
      handoff gaps (missing / unverified / proof_requests) open.
    * RED must be backed by evidence: without a grounded answer_error or
      grounded critical finding it is downgraded to YELLOW. No interruption
      without cited evidence.
    """
    notes: list[str] = []
    level = verdict.deception_level
    has_grounded = any(g.grounded for g in grounded)
    gaps = verdict.handoff.missing or verdict.handoff.unverified or verdict.handoff.proof_requests
    if level == "GREEN" and (has_grounded or gaps):
        level = "YELLOW"
        notes.append("GREEN not allowed while grounded findings or evidence gaps remain.")
    if level == "RED" and not any(
        g.grounded and (g.finding.kind == "answer_error" or g.finding.severity == "critical") for g in grounded
    ):
        level = "YELLOW"
        notes.append("RED downgraded: supervisor cited no grounded contradiction or critical hazard.")
    if level != verdict.deception_level:
        verdict = verdict.model_copy(update={"deception_level": level})
    return verdict, notes


def decide(
    *,
    supervision: Supervision,
    privacy_blocked: bool,
    a_failed: bool,
    b_completed: bool,
    verdict: Verdict | None,
    findings: list[GroundedFinding],
) -> GateDecision:
    """Release gate. Rules are evaluated in order; the first match wins.

    1. privacy_blocked                          -> BLOCKED (nothing is shown)
    2. a_failed                                 -> UNVERIFIED (no usable answer)
    3. supervision == "none"                    -> UNSUPERVISED (study baseline only)
    4. not b_completed or verdict is None       -> UNVERIFIED (fail closed)
    5. any grounded critical/major finding,
       or effective verdict RED                 -> HOLD_FOR_CLINICIAN
    6. effective verdict YELLOW, or any other
       finding (grounded minor or ungrounded)   -> RELEASE_WITH_ADVISORIES
    7. otherwise                                -> RELEASE
    """
    if privacy_blocked:
        return GateDecision(Release.BLOCKED, ["An outbound call was refused by the privacy egress monitor."])
    if a_failed:
        return GateDecision(Release.UNVERIFIED, ["The primary lobe did not produce an answer."])
    if supervision == "none":
        return GateDecision(Release.UNSUPERVISED, ["No supervisory lobe was run (baseline configuration)."])
    if not b_completed or verdict is None:
        return GateDecision(
            Release.UNVERIFIED,
            ["Supervisory review failed or was unparsable; the answer has NOT been checked."],
            advisories=[g for g in findings],
        )

    verdict, notes = effective_verdict(verdict, findings)
    interrupting = [g for g in findings if g.interrupting]
    advisories = [g for g in findings if not g.interrupting]
    reasons = list(notes)
    if interrupting or verdict.deception_level == "RED":
        if interrupting:
            reasons.append(f"{len(interrupting)} evidence-grounded critical/major finding(s).")
        if verdict.deception_level == "RED":
            reasons.append("Supervisor found the answer contradicted by the evidence.")
        return GateDecision(Release.HOLD_FOR_CLINICIAN, reasons, interrupting, advisories, verdict)
    if verdict.deception_level == "YELLOW" or advisories:
        if advisories:
            reasons.append(f"{len(advisories)} advisory finding(s) (minor or not evidence-grounded).")
        if verdict.deception_level == "YELLOW":
            reasons.append("Supervisor verdict YELLOW: material points unverified.")
        return GateDecision(Release.RELEASE_WITH_ADVISORIES, reasons, [], advisories, verdict)
    return GateDecision(Release.RELEASE, ["No findings; supervisor verdict GREEN."], [], [], verdict)
