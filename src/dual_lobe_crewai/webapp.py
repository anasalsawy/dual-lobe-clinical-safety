from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from dual_lobe_crewai.engines import DualLobeEngine
from dual_lobe_clinical.engine import ClinicalDualLobeEngine

try:
    from dual_lobe_crewai.rewrite_experiment import RewriteExperimentEngine
except Exception:
    RewriteExperimentEngine = None


class ChatRequest(BaseModel):
    message: str
    patient_context: str = ""
    loop_cycles: int = 1


app = FastAPI(title="Sawii Dual-Lobe", version="1.0")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "mode": os.getenv("DUAL_LOBE_SERVICE_MODE", "normal")}


@app.post("/chat")
async def chat(req: ChatRequest) -> dict[str, Any]:
    mode = os.getenv("DUAL_LOBE_SERVICE_MODE", "normal").lower().strip()

    if mode == "clinical":
        result = await ClinicalDualLobeEngine().run_clinical(
            query=req.message,
            patient_context=req.patient_context,
        )
        return {
            "mode": "clinical",
            "answer": result.answer,
            "plan_revision": result.plan_revision,
            "timings_ms": result.timings_ms,
            "logical_model_calls": result.logical_model_calls,
        }

    if mode == "experiment":
        if RewriteExperimentEngine is None:
            raise HTTPException(
                status_code=500,
                detail="Experiment engine is not available on this branch.",
            )
        engine = RewriteExperimentEngine()
    else:
        engine = DualLobeEngine()

    if req.loop_cycles > 1:
        results = await engine.run_loop(req.message, cycles=req.loop_cycles)
        result = results[-1]
    else:
        result = await engine.run(req.message)

    return {
        "mode": mode,
        "answer": result.answer,
        "visible_text": result.visible_text(),
        "verdict": result.verdict.model_dump(),
        "timings_ms": result.timings_ms,
        "logical_model_calls": result.logical_model_calls,
    }


def main() -> None:
    import uvicorn

    port = int(os.getenv("PORT", "8080"))
    uvicorn.run("dual_lobe_crewai.webapp:app", host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
