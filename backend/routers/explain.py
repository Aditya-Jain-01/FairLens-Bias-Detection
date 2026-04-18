"""
routers/explain.py
AI Explanation & Q&A Router.

POST /api/v1/explain   — SSE stream of Gemini bias explanation
POST /api/v1/ask       — follow-up Q&A (non-streaming)
"""

import json
import os
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
      2. Build analysis prompt
      3. Collect Gemini stream in a background thread (non-blocking)
      4. Stream chunks back to client as SSE
      5. Parse JSON, save explanation.json, send final done message
    """
    job_id = request.job_id

    # 1. Load results.json
    try:
        results = storage.read_json(job_id, "results.json", bucket="results")
    except Exception as exc:
        logger.error(f"Failed to read results.json for job {job_id}: {exc}")
        raise HTTPException(status_code=404, detail=f"results.json not found for job {job_id}")

    # Return cached explanation if already exists
    if storage.file_exists(job_id, "explanation.json", bucket="results"):
        data = storage.read_json(job_id, "explanation.json", bucket="results")
        return JSONResponse(data)

    # Try to use Vertex AI for real explanation
    try:
        import asyncio
        from services.vertex import stream_gemini, parse_gemini_json
        from prompts.gemini_prompt import SYSTEM_PROMPT, build_analysis_prompt

        prompt = build_analysis_prompt(results)

        async def event_generator():
            accumulated_text = []

            try:
                set_status(job_id, "generating_explanation", "Gemini is analysing bias metrics…", progress=60)

                # Run the SYNCHRONOUS Vertex AI stream in a thread pool so it
                # doesn't block the asyncio event loop
                chunks: list[str] = await asyncio.to_thread(
                    lambda: list(stream_gemini(prompt=prompt, system=SYSTEM_PROMPT))
                )

                # Re-stream chunks to client as SSE
                for chunk_text in chunks:
                    accumulated_text.append(chunk_text)
                    yield f"data: {json.dumps({'chunk': chunk_text})}\n\n"

                # Parse the accumulated JSON response
                full_text = "".join(accumulated_text)
                try:
                    gemini_output = parse_gemini_json(full_text, prompt=prompt, max_retries=1)
                except ValueError as parse_err:
                    logger.error(f"JSON parse failed for job {job_id}: {parse_err}")
                    yield f"data: {json.dumps({'error': 'Gemini returned an unparseable response. The raw text has been logged.'})}\n\n"
                    return

                explanation = {
                    "job_id": job_id,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "summary": gemini_output.get("summary", ""),
                    "severity_label": gemini_output.get("severity_label", ""),
                    "findings": gemini_output.get("findings", []),
                    "recommended_fix": gemini_output.get("recommended_fix", "none"),
                    "recommended_fix_reason": gemini_output.get("recommended_fix_reason", ""),
                    "plain_english": gemini_output.get("plain_english", ""),
                }

                try:
                    storage.write_json(job_id, "explanation.json", explanation, bucket="results")
                except Exception as save_err:
                    logger.error(f"Failed to save explanation.json: {save_err}")

                set_status(job_id, "generating_report", "Generating PDF audit report…", progress=80)
                yield f"data: {json.dumps({'done': True, 'explanation': explanation})}\n\n"

            except RuntimeError as exc:
                logger.error(f"Gemini error for job {job_id}: {exc}")
                yield f"data: {json.dumps({'error': str(exc)})}\n\n"

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

    except ImportError:
        logger.warning("Vertex AI not available — returning stub explanation")
        stub_msg = "AI explanation is unavailable — Vertex AI (Gemini) is not configured on this deployment."
        return JSONResponse({
            "job_id": job_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "plain_english": stub_msg,
            "summary": stub_msg,
            "severity_label": results.get("overall_severity", "unknown").title() + " bias detected",
            "findings": [],
            "recommended_fix": "none",
            "recommended_fix_reason": "",
            "stub": True,
        })



# ── POST /ask ─────────────────────────────────────────────────────────────────

@router.post("/ask")
async def ask(request: AskRequest):
    """
    Answer a follow-up question about the bias audit using Gemini (non-streaming).

    Flow:
      1. Read results.json and explanation.json from storage
      2. Build multi-turn conversation context
      3. Call Gemini for a concise answer (max 300 tokens)
      4. Return {"answer": "..."}
    """
    job_id = request.job_id

    # 1. Load both JSON files
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

    # Try to use Vertex AI
    try:
        from services.vertex import call_gemini_with_history
        from prompts.gemini_prompt import SYSTEM_PROMPT, build_followup_prompt

        # 2. Build multi-turn conversation
        messages = build_followup_prompt(
            results=results,
            explanation=explanation,
            question=request.question,
        )

        # 3. Call Gemini (300 tokens max for concise answers)
        answer = call_gemini_with_history(
            messages=messages,
            system=SYSTEM_PROMPT,
            max_tokens=300,
        )

        return {"answer": answer}

    except ImportError:
        return {
            "answer": "AI Q&A is not available — Vertex AI (Gemini) is not configured. "
                      "Set GCP_PROJECT_ID and install google-cloud-aiplatform to enable this feature."
        }
    except RuntimeError as exc:
        logger.error(f"Gemini Q&A error for job {job_id}: {exc}")
        raise HTTPException(status_code=503, detail=f"AI service error: {exc}")
