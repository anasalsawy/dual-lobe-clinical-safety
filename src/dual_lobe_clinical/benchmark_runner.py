from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from dataclasses import asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from dual_lobe_crewai.agents import make_a, make_b_adversary
from dual_lobe_crewai.runner import run_one

from dual_lobe_clinical.benchmark_validation import assert_valid_cases
from dual_lobe_clinical.engine import ClinicalDualLobeEngine
from dual_lobe_clinical.evidence import FrozenEvidenceStore
from dual_lobe_clinical.evidence_validation import assert_valid_evidence_manifest
from dual_lobe_clinical.guardian import GuardianModelManifest


def to_primitive(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): to_primitive(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_primitive(v) for v in value]
    return value


def load_cases(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


async def run_a0(case: dict[str, Any]) -> dict[str, Any]:
    agent = make_a(tools=None)
    prompt = (
        "You are answering a synthetic clinical research vignette.\n"
        f"PATIENT CONTEXT:\n{json.dumps(case['patient_context'], ensure_ascii=False)}\n\n"
        f"QUERY:\n{case['query']}\n"
        "Return only the candidate answer."
    )
    answer = await run_one(agent, prompt, "Candidate clinical answer.", role_key="A")
    return {"candidate_answer": answer}


async def run_a1(case: dict[str, Any]) -> dict[str, Any]:
    first = await run_a0(case)
    reviewer = make_b_adversary(tools=None)
    prompt = (
        "Self-review baseline. Review the candidate answer using ONLY the same model-side context. "
        "Identify material clinical hazards or omitted context, then return JSON with findings.\n\n"
        f"PATIENT CONTEXT:\n{json.dumps(case['patient_context'], ensure_ascii=False)}\n\n"
        f"QUERY:\n{case['query']}\n\n"
        f"CANDIDATE ANSWER:\n{first['candidate_answer']}\n\n"
        'Return ONLY JSON: {"findings":[{"failure_type":"F01..F23","severity":"info|low|moderate|high|critical","concern":"..."}]}.'
    )
    review = await run_one(reviewer, prompt, "Strict JSON self-review.", role_key="A")
    return {**first, "self_review_raw": review}


async def run_a2(case: dict[str, Any]) -> dict[str, Any]:
    # Independent dual-lobe architecture without external evidence.
    engine = ClinicalDualLobeEngine(evidence_store=FrozenEvidenceStore())
    result = await engine.run_clinical(
        query=case["query"],
        patient_context=json.dumps(case["patient_context"], ensure_ascii=False),
    )
    return to_primitive(asdict(result))


async def run_a3(case: dict[str, Any], evidence_path: str) -> dict[str, Any]:
    engine = ClinicalDualLobeEngine(evidence_path=evidence_path)
    result = await engine.run_clinical(
        query=case["query"],
        patient_context=json.dumps(case["patient_context"], ensure_ascii=False),
    )
    return to_primitive(asdict(result))


async def run_case(case: dict[str, Any], arm: str, evidence_path: str) -> dict[str, Any]:
    if arm == "A0":
        result = await run_a0(case)
    elif arm == "A1":
        result = await run_a1(case)
    elif arm == "A2":
        result = await run_a2(case)
    elif arm == "A3":
        result = await run_a3(case, evidence_path)
    else:
        raise ValueError(f"unknown arm: {arm}")
    return {
        "case_id": case["case_id"],
        "arm": arm,
        "gold": case["gold"],
        "result": result,
    }


def _sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_study_inputs(args, cases: list[dict[str, Any]]) -> None:
    assert_valid_cases(cases)
    evidence = FrozenEvidenceStore.load_json(args.evidence)
    if args.study_mode == "primary":
        assert_valid_evidence_manifest(args.evidence, require_primary_frozen=True)
        if any(bool(c.get("development_only")) for c in cases):
            raise ValueError("primary study refuses development_only benchmark cases")
        if not evidence.records():
            raise ValueError("primary study refuses an empty evidence corpus")
        guardian = GuardianModelManifest.load(args.guardian_manifest)
        guardian.assert_primary_ready(root=Path(args.guardian_manifest).parent.parent)


async def main_async(args) -> None:
    cases = load_cases(args.cases)
    validate_study_inputs(args, cases)
    arms = [x.strip().upper() for x in args.arms.split(",") if x.strip()]
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)

    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "study_mode": args.study_mode,
        "cases_path": str(args.cases),
        "cases_sha256": _sha256(args.cases),
        "evidence_path": str(args.evidence),
        "evidence_sha256": _sha256(args.evidence),
        "guardian_manifest_path": str(args.guardian_manifest),
        "guardian_manifest_sha256": _sha256(args.guardian_manifest),
        "arms": arms,
        "case_ids": [c["case_id"] for c in cases],
    }
    manifest_path = out.with_suffix(out.suffix + ".manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    with out.open("w", encoding="utf-8") as f:
        for case in cases:
            for arm in arms:
                row = await run_case(case, arm, args.evidence)
                f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
                f.flush()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--cases", default="benchmarks/clinical_cases_v1.jsonl")
    p.add_argument("--arms", default="A0,A1,A2,A3")
    p.add_argument("--evidence", default="evidence/evidence_manifest.json")
    p.add_argument("--output", default="results/raw_results.jsonl")
    p.add_argument("--study-mode", choices=["development", "primary"], default="development")
    p.add_argument("--guardian-manifest", default="guardian/guardian_manifest.json")
    args = p.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
