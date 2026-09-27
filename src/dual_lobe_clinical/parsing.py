from __future__ import annotations

from collections.abc import Mapping

from dual_lobe_crewai.json_utils import extract_json_object

from .schemas import (
    ClaimAudit,
    ClaimStatus,
    FailureType,
    HazardFinding,
    Severity,
    SupervisorAssessment,
)


def _severity(value: object) -> Severity:
    try:
        return Severity(str(value or "info").lower())
    except ValueError:
        return Severity.INFO


def _failure(value: object) -> FailureType:
    raw = str(value or "F10").upper()
    for item in FailureType:
        if raw in {item.value, item.name}:
            return item
    return FailureType.UNSUPPORTED_CLINICAL_ASSERTION


def _claim_status(value: object) -> ClaimStatus:
    raw = str(value or "insufficient_evidence").lower()
    try:
        return ClaimStatus(raw)
    except ValueError:
        return ClaimStatus.INSUFFICIENT_EVIDENCE


def assessment_from_mapping(data: Mapping[str, object] | None) -> SupervisorAssessment:
    data = data or {}
    findings: list[HazardFinding] = []
    for item in data.get("findings", []) or []:
        if not isinstance(item, Mapping):
            continue
        try:
            confidence = float(item.get("confidence", 0.0) or 0.0)
        except (TypeError, ValueError):
            confidence = 0.0
        findings.append(
            HazardFinding(
                failure_type=_failure(item.get("failure_type")),
                severity=_severity(item.get("severity")),
                patient_fact=str(item.get("patient_fact") or "").strip(),
                concern=str(item.get("concern") or "").strip(),
                evidence_ids=tuple(str(x) for x in (item.get("evidence_ids") or []) if str(x).strip()),
                confidence=max(0.0, min(1.0, confidence)),
            )
        )

    audits: list[ClaimAudit] = []
    for item in data.get("claim_audits", []) or []:
        if not isinstance(item, Mapping):
            continue
        audits.append(
            ClaimAudit(
                claim_id=str(item.get("claim_id") or f"C{len(audits)+1}"),
                claim_text=str(item.get("claim_text") or "").strip(),
                status=_claim_status(item.get("status")),
                severity_if_wrong=_severity(item.get("severity_if_wrong")),
                evidence_ids=tuple(str(x) for x in (item.get("evidence_ids") or []) if str(x).strip()),
                rationale=str(item.get("rationale") or "").strip(),
            )
        )

    return SupervisorAssessment(
        findings=tuple(findings),
        claim_audits=tuple(audits),
        missing_questions=tuple(str(x) for x in (data.get("missing_questions") or []) if str(x).strip()),
        evidence_conflict=bool(data.get("evidence_conflict", False)),
        supervisor_claims_grounded=bool(data.get("supervisor_claims_grounded", True)),
        notes=tuple(str(x) for x in (data.get("notes") or []) if str(x).strip()),
    )


def assessment_from_json(raw: str) -> SupervisorAssessment:
    parsed = extract_json_object(raw) or {}
    if not isinstance(parsed, Mapping):
        return SupervisorAssessment(supervisor_claims_grounded=False, notes=("unparseable supervisor output",))
    return assessment_from_mapping(parsed)


def merge_assessments(*items: SupervisorAssessment) -> SupervisorAssessment:
    findings: list[HazardFinding] = []
    seen_findings: set[tuple[str, str, str, str]] = set()
    audits: list[ClaimAudit] = []
    seen_claims: set[tuple[str, str]] = set()
    missing: list[str] = []
    notes: list[str] = []

    for item in items:
        for f in item.findings:
            key = (f.failure_type.value, f.severity.value, f.patient_fact, f.concern)
            if key not in seen_findings:
                seen_findings.add(key)
                findings.append(f)
        for audit in item.claim_audits:
            key = (audit.claim_id, audit.claim_text)
            if key not in seen_claims:
                seen_claims.add(key)
                audits.append(audit)
        for q in item.missing_questions:
            if q not in missing:
                missing.append(q)
        for note in item.notes:
            if note not in notes:
                notes.append(note)

    return SupervisorAssessment(
        findings=tuple(findings),
        claim_audits=tuple(audits),
        missing_questions=tuple(missing),
        evidence_conflict=any(x.evidence_conflict for x in items),
        supervisor_claims_grounded=all(x.supervisor_claims_grounded for x in items),
        notes=tuple(notes),
    )
