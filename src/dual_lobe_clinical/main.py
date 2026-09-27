from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict

from .engine import ClinicalDualLobeEngine


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="dual-lobe-clinical",
        description="Run the publication-oriented Dual-Lobe clinical safety research runtime.",
    )
    parser.add_argument("--query", required=True)
    parser.add_argument("--patient-context", required=True)
    parser.add_argument("--evidence", default="evidence/evidence_manifest.json")
    args = parser.parse_args()

    engine = ClinicalDualLobeEngine(evidence_path=args.evidence)
    result = asyncio.run(
        engine.run_clinical(
            query=args.query,
            patient_context=args.patient_context,
        )
    )
    print(json.dumps(asdict(result), indent=2, default=str))


if __name__ == "__main__":
    main()
