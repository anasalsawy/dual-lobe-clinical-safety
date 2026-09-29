from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

from dual_lobe_clinical.engine import ClinicalDualLobeEngine, ClinicalRequest
from dual_lobe_crewai.engines import DualLobeEngine


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
        result = await ClinicalDualLobeEngine().run(
            ClinicalRequest(question=req.message, record=req.patient_context)
        )
        return {
            "mode": "clinical",
            "release": getattr(result.release, "value", str(result.release)),
            "answer": result.answer,
            "visible_text": result.visible_text(),
            "timings_ms": result.timings_ms,
            "logical_model_calls": result.logical_model_calls,
        }

    engine = DualLobeEngine()
    if req.loop_cycles > 1:
        result = (await engine.run_loop(req.message, cycles=req.loop_cycles))[-1]
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
