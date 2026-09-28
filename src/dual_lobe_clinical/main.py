from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

from .engine import ClinicalDualLobeEngine, ClinicalRequest


def _load_record(path: str):
    text = Path(path).read_text(encoding="utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text  # free-text note


async def _amain(args) -> int:
    engine = ClinicalDualLobeEngine(supervision=args.supervision, live_b=args.live_b)
    request = ClinicalRequest(
        question=args.question,
        record=_load_record(args.record),
        index_date=date.fromisoformat(args.index_date) if args.index_date else None,
    )
    result = await engine.run(request)
    print(result.visible_text())
    if args.show_meta:
        meta = {
            "release": result.release.value,
            "requires_acknowledgement": result.decision.requires_acknowledgement,
            "reasons": result.decision.reasons,
            "findings_deidentified": result.findings_deidentified,
            "fact_paths": result.fact_paths,
            "privacy_receipt": {
                k: v for k, v in result.receipt.__dict__.items() if k != "audit_log"
            },
            "timings_ms": result.timings_ms,
            "logical_model_calls": result.logical_model_calls,
        }
        print("\n--- metadata (de-identified) ---")
        print(json.dumps(meta, indent=2, ensure_ascii=False, default=str))
    return 0


def main() -> None:
    load_dotenv()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    p = argparse.ArgumentParser(description="Dual-Lobe clinical safety proxy (research use only).")
    p.add_argument("--question", required=True, help="The clinician's question.")
    p.add_argument("--record", required=True, help="Path to the patient record (JSON or plain text).")
    p.add_argument("--index-date", default=None, help="Reference date for relative dates (YYYY-MM-DD); default today.")
    p.add_argument("--supervision", choices=["dual_lobe", "answer_verifier", "none"], default="dual_lobe")
    p.add_argument("--live-b", action=argparse.BooleanOptionalAction, default=None)
    p.add_argument("--show-meta", action="store_true")
    args = p.parse_args()
    raise SystemExit(asyncio.run(_amain(args)))


if __name__ == "__main__":
    main()
