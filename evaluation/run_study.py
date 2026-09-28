"""Run the omission benchmark under each supervision arm with real models.

Arms (same A model, same B model, same de-identified record in all arms):
  a_only          - A answers; no supervisory lobe (baseline)
  answer_verifier - a conventional verifier checks A's answer against the record
  dual_lobe       - independent pre-answer context scan + final audit (this work)
  dual_lobe_live  - dual_lobe plus live B observation during A's run

Every remote-bound payload is also checked against the case's planted
identifiers by a probe installed AFTER the privacy monitor, so a leak in a
real run is measured, not assumed.

Usage:
    python evaluation/run_study.py --arms a_only answer_verifier dual_lobe --repeats 3
    python evaluation/score.py results/study_<stamp>.jsonl
Only de-identified outputs are written.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

from dual_lobe_crewai.runner import register_egress_filter, unregister_egress_filter
from dual_lobe_clinical import egress
from dual_lobe_clinical.engine import ClinicalDualLobeEngine, ClinicalRequest
from dual_lobe_clinical.locality import is_local_spec

ARMS = {
    "a_only": dict(supervision="none", live_b=False),
    "answer_verifier": dict(supervision="answer_verifier", live_b=False),
    "dual_lobe": dict(supervision="dual_lobe", live_b=False),
    "dual_lobe_live": dict(supervision="dual_lobe", live_b=True),
}


class LeakProbe:
    def __init__(self) -> None:
        self.planted: list[str] = []
        self.leaks: list[str] = []
        self.remote_payloads = 0

    def __call__(self, spec, text: str) -> str:
        if not is_local_spec(spec):
            self.remote_payloads += 1
            low = text.casefold()
            self.leaks.extend(p for p in self.planted if p.casefold() in low)
        return text


def provenance(cases_path: str) -> dict:
    """Frozen identity of the benchmark, code and models used in a run."""
    import hashlib
    import os
    import subprocess

    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout.strip())
    except Exception:
        commit, dirty = "unknown", None
    return {
        "cases_sha256": hashlib.sha256(Path(cases_path).read_bytes()).hexdigest(),
        "code_commit": commit,
        "code_dirty": dirty,
        "a_model": os.getenv("DUAL_LOBE_A_MODEL", ""),
        "b_model": os.getenv("DUAL_LOBE_B_VERIFY_MODEL") or os.getenv("DUAL_LOBE_B_MODEL", ""),
        "b_locality_mode": os.getenv("DUAL_LOBE_CLINICAL_B_LOCALITY", "require"),
    }


async def run(args) -> Path:
    suite = json.loads(Path(args.cases).read_text(encoding="utf-8"))
    prov = provenance(args.cases)
    index_date = date.fromisoformat(suite["index_date"])
    cases = [c for c in suite["cases"] if not args.only or c["id"] in args.only]
    done: set[tuple] = set()
    if args.resume:
        # Append to an interrupted run (e.g. a provider's daily quota ran out),
        # skipping every case/arm/repeat that already has a row. Rows that
        # failed with an exception are retried; fail-closed releases are kept.
        out = Path(args.resume)
        for line in out.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            if "error" not in r:
                done.add((r["case_id"], r["arm"], r["repeat"]))
    else:
        out = Path(args.out_dir) / f"study_{time.strftime('%Y%m%d_%H%M%S')}.jsonl"
        out.parent.mkdir(parents=True, exist_ok=True)

    egress.install()  # monitor first, probe second: the probe sees what actually leaves
    probe = LeakProbe()
    register_egress_filter(probe)
    try:
        with out.open("a" if args.resume else "w", encoding="utf-8") as fh:
            for repeat in range(args.repeats):
                for case in cases:
                    for arm in args.arms:
                        if (case["id"], arm, repeat) in done:
                            continue
                        probe.planted, probe.leaks, probe.remote_payloads = list(case.get("phi", [])), [], 0
                        engine = ClinicalDualLobeEngine(**ARMS[arm])
                        t0 = time.perf_counter()
                        try:
                            result = await engine.run(
                                ClinicalRequest(question=case["question"], record=case["record"], index_date=index_date)
                            )
                            row = {
                                "case_id": case["id"], "case_type": case["type"], "arm": arm, "repeat": repeat,
                                "release": result.release.value,
                                "reasons": result.decision.reasons,
                                "answer_deidentified": result.answer_deidentified,
                                "findings": result.findings_deidentified,
                                "scan": result.scan_deidentified,
                                "fact_paths": result.fact_paths,
                                "malformed_items": result.malformed_items,
                                "verdict": result.verdict.deception_level if result.verdict else None,
                                "privacy": {
                                    "identifiers_protected": result.receipt.identifiers_protected,
                                    "residual_sweep": result.receipt.residual_sweep,
                                    "b_locality": result.receipt.b_locality,
                                    "blocked": result.receipt.outbound_blocked,
                                    "key_destroyed": result.receipt.key_destroyed,
                                    "remote_payloads": probe.remote_payloads,
                                    "planted_identifier_leaks": sorted(set(probe.leaks)),
                                },
                                "timings_ms": result.timings_ms,
                                "logical_model_calls": result.logical_model_calls,
                            }
                        except Exception as exc:
                            row = {"case_id": case["id"], "case_type": case["type"], "arm": arm, "repeat": repeat,
                                   "error": f"{type(exc).__name__}: {exc}",
                                   "elapsed_ms": int((time.perf_counter() - t0) * 1000)}
                        row["provenance"] = prov
                        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
                        fh.flush()
                        print(f"{case['id']} {arm} r{repeat}: {row.get('release', row.get('error'))}")
    finally:
        unregister_egress_filter(probe)
    return out


def main() -> None:
    load_dotenv()
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", default="benchmarks/clinical/cases.json")
    ap.add_argument("--arms", nargs="+", default=["a_only", "answer_verifier", "dual_lobe"], choices=list(ARMS))
    ap.add_argument("--repeats", type=int, default=1)
    ap.add_argument("--only", nargs="*", default=None, help="Case IDs to run.")
    ap.add_argument("--out-dir", default="results")
    ap.add_argument("--resume", default=None, help="Existing study JSONL to append to, skipping completed rows.")
    args = ap.parse_args()
    path = asyncio.run(run(args))
    print(f"\nWrote {path}. Score with: python evaluation/score.py {path}")


if __name__ == "__main__":
    main()
