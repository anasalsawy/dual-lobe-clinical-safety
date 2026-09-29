from __future__ import annotations

import argparse
import asyncio
import sys

from dotenv import load_dotenv

from .rewrite_experiment import RewriteExperimentEngine


async def _amain(task: str, loop_cycles: int) -> None:
    engine = RewriteExperimentEngine()
    if loop_cycles > 1:
        results = await engine.run_loop(task, cycles=loop_cycles)
        result = results[-1]
    else:
        result = await engine.run(task)
    print(result.visible_text())


def main() -> None:
    load_dotenv()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    p = argparse.ArgumentParser(description="Dual-Lobe controlled rewrite experiment.")
    p.add_argument("--task", required=True)
    p.add_argument("--loop-cycles", type=int, default=1)
    args = p.parse_args()
    asyncio.run(_amain(args.task, args.loop_cycles))


if __name__ == "__main__":
    main()
