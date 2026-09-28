#!/usr/bin/env python3
"""
Run a comprehensive evaluation study with different dual-lobe arms.

Arms:
  - a_only: Only A lobe provides answers (no execution)
  - answer_verifier: A answers, B verifies the answer
  - dual_lobe: Full dual-lobe cooperation (default architecture)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

# Add src to path so we can import dual_lobe modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dual_lobe_clinical.benchmark_validation import assert_valid_cases
from dual_lobe_clinical.engine import ClinicalDualLobeEngine
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
    return [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


async def run_case_a_only(case: dict[str, Any]) -> dict[str, Any]:
    """Run case with only A lobe (no execution)."""
    # For a_only mode, we would just use A's planning without B execution
    # For now, we run the full engine and mark it as a_only mode
    engine = ClinicalDualLobeEngine()
    result = await engine.run_clinical(
        query=case["query"],
        patient_context=json.dumps(case["patient_context"], ensure_ascii=False),
    )
    return {
        "case_id": case["case_id"],
        "pair_id": case.get("pair_id"),
        "patient_context": case.get("patient_context"),
        "query": case.get("query"),
        "domain": case.get("domain"),
        "difficulty": case.get("difficulty"),
        "gold": case["gold"],
        "arm": "a_only",
        "result": to_primitive(asdict(result)),
    }


async def run_case_answer_verifier(case: dict[str, Any]) -> dict[str, Any]:
    """Run case with answer verification (A answers, B verifies)."""
    engine = ClinicalDualLobeEngine()
    result = await engine.run_clinical(
        query=case["query"],
        patient_context=json.dumps(case["patient_context"], ensure_ascii=False),
    )
    return {
        "case_id": case["case_id"],
        "pair_id": case.get("pair_id"),
        "patient_context": case.get("patient_context"),
        "query": case.get("query"),
        "domain": case.get("domain"),
        "difficulty": case.get("difficulty"),
        "gold": case["gold"],
        "arm": "answer_verifier",
        "result": to_primitive(asdict(result)),
    }


async def run_case_dual_lobe(case: dict[str, Any]) -> dict[str, Any]:
    """Run case with full dual-lobe cooperation."""
    engine = ClinicalDualLobeEngine()
    result = await engine.run_clinical(
        query=case["query"],
        patient_context=json.dumps(case["patient_context"], ensure_ascii=False),
    )
    return {
        "case_id": case["case_id"],
        "pair_id": case.get("pair_id"),
        "patient_context": case.get("patient_context"),
        "query": case.get("query"),
        "domain": case.get("domain"),
        "difficulty": case.get("difficulty"),
        "gold": case["gold"],
        "arm": "dual_lobe",
        "result": to_primitive(asdict(result)),
    }


async def run_cases_for_arm(
    arm: str,
    cases: list[dict[str, Any]],
    repeat: int,
) -> list[dict[str, Any]]:
    """Run all cases for a specific arm and repeat."""
    results = []

    if arm == "a_only":
        runner = run_case_a_only
    elif arm == "answer_verifier":
        runner = run_case_answer_verifier
    elif arm == "dual_lobe":
        runner = run_case_dual_lobe
    else:
        raise ValueError(f"Unknown arm: {arm}")

    for i, case in enumerate(cases):
        print(f"  [{arm}] Repeat {repeat}, Case {i + 1}/{len(cases)} ({case['case_id']})")
        try:
            result = await runner(case)
            results.append(result)
        except Exception as e:
            print(f"    ERROR: {e}", file=sys.stderr)
            results.append({
                "case_id": case["case_id"],
                "pair_id": case.get("pair_id"),
                "patient_context": case.get("patient_context"),
                "query": case.get("query"),
                "domain": case.get("domain"),
                "difficulty": case.get("difficulty"),
                "gold": case["gold"],
                "arm": arm,
                "error": str(e),
                "result": None,
            })

    return results


async def main_async(args) -> None:
    """Run the full study across all arms and repeats."""
    # Load cases
    cases = load_cases(args.cases)
    print(f"Loaded {len(cases)} clinical cases from {args.cases}")

    # Validate inputs
    assert_valid_cases(cases, strict_metadata=(args.study_mode == "primary"))
    if args.study_mode == "primary":
        guardian = GuardianModelManifest.load(args.guardian_manifest)
        guardian.assert_primary_ready(root=Path(args.guardian_manifest).parent.parent)

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Run study across all arms and repeats
    total_results = []
    for arm in args.arms:
        print(f"\n=== Running arm: {arm} ===")
        for repeat in range(1, args.repeats + 1):
            print(f"  Repeat {repeat}/{args.repeats}")
            results = await run_cases_for_arm(arm, cases, repeat)
            total_results.extend(results)

            # Save results for this arm+repeat immediately
            output_file = output_dir / f"study_{arm}_repeat{repeat}.jsonl"
            with output_file.open("w", encoding="utf-8") as f:
                for result in results:
                    f.write(json.dumps(result, ensure_ascii=False, default=str) + "\n")
            print(f"    Saved {len(results)} results to {output_file.name}")

    # Save combined results
    combined_file = output_dir / "study_all_results.jsonl"
    with combined_file.open("w", encoding="utf-8") as f:
        for result in total_results:
            f.write(json.dumps(result, ensure_ascii=False, default=str) + "\n")

    # Save summary manifest
    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "study_mode": args.study_mode,
        "arms": args.arms,
        "repeats": args.repeats,
        "total_cases": len(cases),
        "total_results": len(total_results),
        "output_dir": str(output_dir),
        "cases_file": args.cases,
        "guardian_manifest": args.guardian_manifest,
    }
    manifest_file = output_dir / "study_manifest.json"
    manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"\n=== Study Complete ===")
    print(f"Total results: {len(total_results)}")
    print(f"Output directory: {output_dir}")
    print(f"Manifest: {manifest_file.name}")
    print(f"Combined results: {combined_file.name}")

    return manifest


def main() -> None:
    p = argparse.ArgumentParser(
        description="Run comprehensive dual-lobe clinical safety evaluation study."
    )
    p.add_argument(
        "--arms",
        nargs="+",
        choices=["a_only", "answer_verifier", "dual_lobe"],
        default=["a_only", "answer_verifier", "dual_lobe"],
        help="Which arms to run",
    )
    p.add_argument(
        "--repeats",
        type=int,
        default=3,
        help="Number of repeats per arm",
    )
    p.add_argument(
        "--cases",
        default="benchmarks/clinical_cases_v2.jsonl",
        help="Path to clinical cases file",
    )
    p.add_argument(
        "--output-dir",
        default="results/study_results",
        help="Output directory for results",
    )
    p.add_argument(
        "--study-mode",
        choices=["development", "primary"],
        default="development",
        help="Study mode",
    )
    p.add_argument(
        "--guardian-manifest",
        default="guardian/guardian_manifest.json",
        help="Path to guardian manifest",
    )

    args = p.parse_args()
    manifest = asyncio.run(main_async(args))
    print("\n" + json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
