"""
routers/explain.py
AI Explanation & Q&A Router.

POST /api/v1/explain   — SSE stream of Gemini bias explanation
POST /api/v1/ask       — follow-up Q&A (non-streaming)

Uses services.gemini exclusively (stdlib urllib, no SDK required).
Requires GEMINI_API_KEY env var (free key from aistudio.google.com/apikey).
"""

import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel

from services import storage
from services.status import set_status

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Pydantic request models ───────────────────────────────────────────────────

class ExplainRequest(BaseModel):
    job_id: str


class AskRequest(BaseModel):
    job_id: str
    question: str


# ── POST /explain ─────────────────────────────────────────────────────────────

@router.post("/explain")
async def explain(request: ExplainRequest):
    """
    Stream a Gemini-generated bias explanation as Server-Sent Events.

    Flow:
      1. Read results.json from storage
      2. If explanation.json already exists, return it as JSON immediately
      3. Call services.gemini.generate_explanation in a thread pool
      4. Stream progress chunks as SSE, then send the final explanation
      5. Save explanation.json and update job status
    """
    job_id = request.job_id

    # 1. Load results.json
    try:
        results = storage.read_json(job_id, "results.json", bucket="results")
    except Exception as exc:
        logger.error(f"Failed to read results.json for job {job_id}: {exc}")
        raise HTTPException(status_code=404, detail=f"results.json not found for job {job_id}")

    # 2. Return cached explanation if it already exists
    if storage.file_exists(job_id, "explanation.json", bucket="results"):
        data = storage.read_json(job_id, "explanation.json", bucket="results")
        return JSONResponse(data)

    # 3. Generate explanation via services.gemini (no SDK, pure urllib)
    async def event_generator():
        try:
            import asyncio
            from services.gemini import generate_explanation

            set_status(job_id, "generating_explanation", "Gemini is analysing bias metrics…", progress=60)

            # Run the synchronous Gemini call in a thread pool so it
            # doesn't block the asyncio event loop
            explanation = await asyncio.to_thread(generate_explanation, results, job_id)

            # Emit the plain-english summary as a stream chunk so the
            # frontend shows progressive text while waiting
            plain = explanation.get("plain_english", "")
            if plain:
                yield f"data: {json.dumps({'chunk': plain})}\n\n"

            # Save explanation.json
            try:
                storage.write_json(job_id, "explanation.json", explanation, bucket="results")
            except Exception as save_err:
                logger.error(f"Failed to save explanation.json for job {job_id}: {save_err}")

            set_status(job_id, "generating_report", "Generating PDF audit report…", progress=80)
            yield f"data: {json.dumps({'done': True, 'explanation': explanation})}\n\n"

        except RuntimeError as exc:
            err_msg = str(exc)
            logger.error(f"Gemini error for job {job_id}: {err_msg}")
            yield f"data: {json.dumps({'error': err_msg})}\n\n"

        except Exception as exc:
            logger.error(f"Unexpected error in explain for job {job_id}: {exc}")
            yield f"data: {json.dumps({'error': f'Unexpected error: {exc}'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ── POST /ask ─────────────────────────────────────────────────────────────────

@router.post("/ask")
async def ask(request: AskRequest):
    """
    Answer a follow-up question about the bias audit using Gemini (non-streaming).

    Flow:
      1. Read results.json and explanation.json from storage
      2. Build multi-turn conversation context
      3. Call services.gemini.answer_question (max 512 tokens)
      4. Return {"answer": "..."}
    """
    job_id = request.job_id

    # Load context files
    try:
        results = storage.read_json(job_id, "results.json", bucket="results")
    except Exception:
        raise HTTPException(status_code=404, detail=f"results.json not found for job {job_id}")

    try:
        explanation = storage.read_json(job_id, "explanation.json", bucket="results")
    except Exception:
        raise HTTPException(
            status_code=404,
            detail=f"explanation.json not found for job {job_id}. Run /explain first.",
        )

    try:
        from services.gemini import answer_question
        from prompts.gemini_prompt import SYSTEM_PROMPT, build_followup_prompt

        messages = build_followup_prompt(
            results=results,
            explanation=explanation,
            question=request.question,
        )

        answer = answer_question(messages=messages, system=SYSTEM_PROMPT, max_tokens=512)
        return {"answer": answer}

    except RuntimeError as exc:
        logger.error(f"Gemini Q&A error for job {job_id}: {exc}")
        raise HTTPException(status_code=503, detail=f"AI service error: {exc}")
