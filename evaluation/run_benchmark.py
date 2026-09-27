from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from dual_lobe_crewai.agents import make_a, make_b_adversary
from dual_lobe_crewai.runner import run_one

from dual_lobe_clinical.engine import ClinicalDualLobeEngine
from dual_lobe_clinical.evidence import FrozenEvidenceStore


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
        'Return ONLY JSON: {"findings":[{"failure_type":"F01..F18","severity":"info|low|moderate|high|critical","concern":"..."}]}.'
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
    return asdict(result)


async def run_a3(case: dict[str, Any], evidence_path: str) -> dict[str, Any]:
    engine = ClinicalDualLobeEngine(evidence_path=evidence_path)
    result = await engine.run_clinical(
        query=case["query"],
        patient_context=json.dumps(case["patient_context"], ensure_ascii=False),
    )
    return asdict(result)


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


async def main_async(args) -> None:
    cases = load_cases(args.cases)
    arms = [x.strip().upper() for x in args.arms.split(",") if x.strip()]
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)

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
    args = p.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
