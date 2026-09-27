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
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


async def run_case(case: dict[str, Any]) -> dict[str, Any]:
    result = await ClinicalDualLobeEngine().run_clinical(
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
        "result": to_primitive(asdict(result)),
    }


def _sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_study_inputs(args, cases: list[dict[str, Any]]) -> None:
    if args.study_mode == "primary" and any(bool(c.get("development_only")) for c in cases):
        raise ValueError("primary study refuses development_only benchmark cases")
    assert_valid_cases(cases, strict_metadata=(args.study_mode == "primary"))
    if args.study_mode == "primary":
        guardian = GuardianModelManifest.load(args.guardian_manifest)
        guardian.assert_primary_ready(root=Path(args.guardian_manifest).parent.parent)


async def main_async(args) -> None:
    cases = load_cases(args.cases)
    validate_study_inputs(args, cases)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)

    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "study_mode": args.study_mode,
        "cases_path": str(args.cases),
        "cases_sha256": _sha256(args.cases),
        "guardian_manifest_path": str(args.guardian_manifest),
        "guardian_manifest_sha256": _sha256(args.guardian_manifest),
        "case_ids": [c["case_id"] for c in cases],
        "system": "dual_lobe_clinical",
    }
    out.with_suffix(out.suffix + ".manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    with out.open("w", encoding="utf-8") as f:
        for case in cases:
            f.write(json.dumps(await run_case(case), ensure_ascii=False, default=str) + "\n")
            f.flush()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--cases", default="benchmarks/clinical_cases_v2.jsonl")
    p.add_argument("--output", default="results/raw_results.jsonl")
    p.add_argument("--study-mode", choices=["development", "primary"], default="development")
    p.add_argument("--guardian-manifest", default="guardian/guardian_manifest.json")
    asyncio.run(main_async(p.parse_args()))


if __name__ == "__main__":
    main()
