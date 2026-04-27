"""
routers/worker.py
Phase 2.1 — Internal Cloud Tasks worker endpoint.

POST /internal/run-job
  Called by Google Cloud Tasks (not the browser). Protected by
  X-Internal-Secret header to prevent public access.

This endpoint runs the full bias pipeline synchronously, which is
safe because Cloud Tasks gives it its own dedicated HTTP call with
a configurable timeout (up to 30 min on Cloud Run).
"""

import os
import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()

_SECRET = os.getenv("INTERNAL_WORKER_SECRET", "")


class WorkerRequest(BaseModel):
    job_id: str
    config: dict


def _verify_worker_secret(request: Request) -> None:
    """Reject requests that don't carry the correct internal secret."""
    if not _SECRET:
        # If no secret is configured, block all calls to prevent accidental exposure
        raise HTTPException(status_code=503, detail="Worker endpoint not configured.")
    incoming = request.headers.get("X-Internal-Secret", "")
    if incoming != _SECRET:
        raise HTTPException(status_code=403, detail="Forbidden.")


@router.post("/internal/run-job", include_in_schema=False)
def run_job(req: WorkerRequest, request: Request):
    """
    Entry point called by Cloud Tasks. Runs the full bias analysis pipeline.
    Returns 200 on success, 500 on failure (Cloud Tasks will retry on non-2xx).

    NOTE: Defined as a regular (non-async) function so FastAPI runs it in a
    thread pool executor, preventing the CPU-bound ML pipeline from blocking
    the asyncio event loop for the 30–60 seconds analysis takes.
    """
    _verify_worker_secret(request)

    job_id = req.job_id
    config  = req.config

    logger.info(f"[Worker] Starting pipeline for job {job_id}")

    try:
        from services.analysis_pipeline import run_full_analysis
        from services.inference import run_inference
        from services.status import set_status
        from services import storage

        # Step 1 — Save config
        set_status(job_id, "configuring", "Saving configuration…")
        storage.write_json(job_id, "config.json", config, bucket="uploads")

        # Step 2 — Run model inference
        set_status(job_id, "running_inference", "Running model inference…")
        run_inference(job_id, config)

        # Step 3 — Run full bias analysis (includes cache write)
        run_full_analysis(job_id)

        logger.info(f"[Worker] Pipeline complete for job {job_id}")
        return JSONResponse({"job_id": job_id, "status": "complete"})

    except Exception as exc:
        logger.error(f"[Worker] Pipeline failed for job {job_id}: {exc}")
        try:
            from services.status import set_status
            set_status(job_id, "error", error=str(exc), message=f"Pipeline failed: {exc}")
        except Exception:
            pass
        return JSONResponse(
            {"job_id": job_id, "status": "failed", "error": str(exc)}, 
            status_code=200
        )
