from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict
from enum import Enum

from .engine import ClinicalDualLobeEngine


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="dual-lobe-clinical",
        description="Run the clinical Dual-Lobe planner-executor runtime.",
    )
    parser.add_argument("--query", required=True, help="User task or command.")
    parser.add_argument(
        "--patient-context",
        default="",
        help="Local clinical context/data available to the execution lobe.",
    )
    args = parser.parse_args()

    result = asyncio.run(
        ClinicalDualLobeEngine().run_clinical(
            query=args.query,
            patient_context=args.patient_context,
        )
    )

    def stable_json(value):
        if isinstance(value, Enum):
            return value.value
        if hasattr(value, "model_dump"):
            return value.model_dump()
        return str(value)

    print(json.dumps(asdict(result), indent=2, default=stable_json))


if __name__ == "__main__":
    main()
