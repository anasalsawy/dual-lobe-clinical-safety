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
        description="Run the Dual-Lobe clinical safety research runtime.",
    )
    parser.add_argument("--query", required=True)
    parser.add_argument("--patient-context", required=True)
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
        return str(value)

    print(json.dumps(asdict(result), indent=2, default=stable_json))


if __name__ == "__main__":
    main()
