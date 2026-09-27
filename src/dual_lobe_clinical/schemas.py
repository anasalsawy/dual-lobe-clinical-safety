from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Severity(str, Enum):
    INFO = "info"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class Decision(str, Enum):
    PASS = "pass"
    WARN = "warn"
    REVISE = "revise"
    BLOCK = "block"
    ESCALATE = "escalate"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class ClaimStatus(str, Enum):
    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class FailureType(str, Enum):
    OMITTED_CONTEXT = "F01"
    MISSED_CONTRAINDICATION = "F02"
    MISSED_DRUG_INTERACTION = "F03"
    MISSED_DISEASE_DRUG_INTERACTION = "F04"
    ALLERGY_OVERSIGHT = "F05"
    PREGNANCY_LACTATION_RISK = "F06"
    RENAL_HEPATIC_DOSING_RISK = "F07"
    AGE_SPECIFIC_RISK = "F08"
    MISSED_RED_FLAG = "F09"
    UNSUPPORTED_CLINICAL_ASSERTION = "F10"
    HALLUCINATED_EVIDENCE = "F11"
    OUTDATED_OR_IRRELEVANT_EVIDENCE = "F12"
    UNSAFE_CERTAINTY = "F13"
    CORRELATED_AB_FAILURE = "F14"
    FALSE_POSITIVE_WARNING = "F15"
    UNNECESSARY_BLOCK = "F16"
    EVIDENCE_CONFLICT = "F17"
    CONTEXT_MISINTERPRETATION = "F18"


@dataclass(frozen=True)
class EvidenceRecord:
    evidence_id: str
    source: str
    title: str
    version_or_date: str
    excerpt: str
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class HazardFinding:
    failure_type: FailureType
    severity: Severity
    patient_fact: str
    concern: str
    evidence_ids: tuple[str, ...] = ()
    confidence: float = 0.0

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")


@dataclass(frozen=True)
class ClaimAudit:
    claim_id: str
    claim_text: str
    status: ClaimStatus
    severity_if_wrong: Severity
    evidence_ids: tuple[str, ...] = ()
    rationale: str = ""


@dataclass(frozen=True)
class SupervisorAssessment:
    findings: tuple[HazardFinding, ...] = ()
    claim_audits: tuple[ClaimAudit, ...] = ()
    missing_questions: tuple[str, ...] = ()
    evidence_conflict: bool = False
    supervisor_claims_grounded: bool = True
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class GateResult:
    decision: Decision
    reasons: tuple[str, ...] = ()
    unresolved_evidence_ids: tuple[str, ...] = ()
