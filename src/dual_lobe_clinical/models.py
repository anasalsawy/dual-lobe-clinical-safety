from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

from dual_lobe_crewai.models import Verdict

# What the supervisory lobe can report. Each kind is one failure mode of the
# primary lobe (see docs/METHODS.md, "Failure taxonomy").
FindingKind = Literal[
    "unasked_hazard",       # record holds a risk the question did not ask about
    "missing_information",  # a safe answer needs data the record does not have
    "answer_error",         # A's answer is contradicted by the record or is clinically wrong here
    "unsupported_claim",    # A asserts a patient-specific fact the record does not support
]
Severity = Literal["critical", "major", "minor"]


class ClinicalFinding(BaseModel):
    kind: FindingKind
    severity: Severity
    statement: str = Field(min_length=1)
    patient_evidence: list[str] = Field(default_factory=list)  # F#, Q (question), A (answer)
    quote: str = ""
    knowledge_evidence: list[str] = Field(default_factory=list)  # K#
    recommended_check: str = ""


class ContextScan(BaseModel):
    """B's independent reading of the record, made before it sees A's answer."""

    context_summary: str = ""
    hazards: list[ClinicalFinding] = Field(default_factory=list)


class ClinicalReview(BaseModel):
    answer_verdict: Verdict
    findings: list[ClinicalFinding] = Field(default_factory=list)
    context_summary: str = ""


class ResidualSweep(BaseModel):
    class Item(BaseModel):
        text: str
        category: str = "OTHER"

    identifiers: list[Item] = Field(default_factory=list)


class Release(str, Enum):
    RELEASE = "RELEASE"
    RELEASE_WITH_ADVISORIES = "RELEASE_WITH_ADVISORIES"
    HOLD_FOR_CLINICIAN = "HOLD_FOR_CLINICIAN"
    UNVERIFIED = "UNVERIFIED"
    UNSUPERVISED = "UNSUPERVISED"
    BLOCKED = "BLOCKED"


Supervision = Literal["dual_lobe", "answer_verifier", "none"]
