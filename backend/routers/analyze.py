"""
routers/analyze.py
Handles job configuration and kicks off the async analysis pipeline.

POST /api/v1/analyze/configure
GET  /api/v1/status/{job_id}
"""

import asyncio
import os
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from services import storage
from services.status import set_status, get_status
from services.inference import run_inference

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Pydantic models ───────────────────────────────────────────────────────────

class ConfigureRequest(BaseModel):
    job_id: str
    target_column: str
    protected_attributes: list[str]
    positive_outcome_label: int = 1


# ── Background pipeline ───────────────────────────────────────────────────────

async def _run_pipeline(job_id: str, config: dict):
    """
    Full pipeline executed in the background after /configure is called.
    Stages: uploading → configuring → running_inference → computing_metrics → complete
    """
    try:
        # Step 1: Save config.json
        set_status(job_id, "configuring", "Saving configuration...")
        storage.write_json(job_id, "config.json", config, bucket="uploads")

        # Step 2: Run model inference
        set_status(job_id, "running_inference", "Running model inference...")
        await asyncio.get_running_loop().run_in_executor(None, run_inference, job_id, config)

        # Step 3: Run bias analysis
        await _run_analysis_or_mock(job_id, config)

    except Exception as e:
        logger.error(f"Pipeline failed for job {job_id}: {e}")
        set_status(job_id, "error", error=str(e), message=f"Pipeline failed: {e}")


async def _run_analysis_or_mock(job_id: str, config: dict):
    """
    Runs the bias analysis pipeline if available, or falls back to mock data.
    """
    set_status(job_id, "computing_metrics", "Computing fairness metrics...")

    # If results already exist (demo job), skip ahead
    if storage.file_exists(job_id, "results.json", bucket="results"):
        await asyncio.sleep(1)
        set_status(job_id, "generating_explanation", "Generating AI explanation...")
        await asyncio.sleep(1)
        set_status(job_id, "generating_report", "Building audit report...")
        await asyncio.sleep(1)
        set_status(job_id, "complete", "Audit complete!")
        return

    # Check if USE_MOCK_PIPELINE is set — useful for frontend dev
    if os.getenv("USE_MOCK_PIPELINE", "false").lower() == "true":
        await _inject_mock_results(job_id, config)
        return

    # Run bias analysis pipeline
    try:
        from services.analysis_pipeline import run_full_analysis
        await asyncio.get_running_loop().run_in_executor(None, run_full_analysis, job_id)
        logger.info(f"Analysis complete for job {job_id}")
        # After analysis, status is at 'generating_explanation'
        # /explain endpoint handles the rest when called by the frontend
    except ImportError:
        logger.warning("analysis_pipeline not available — leaving at computing_metrics")
    except Exception as e:
        logger.error(f"Analysis failed for job {job_id}: {e}")
        set_status(job_id, "error", error=str(e), message=f"Analysis failed: {e}")


async def _inject_mock_results(job_id: str, config: dict):
    """Inject mock results so the full frontend flow can be tested locally."""
    from mocks.mock_data import MOCK_RESULTS, MOCK_EXPLANATION

    await asyncio.sleep(2)
    results = dict(MOCK_RESULTS)
    results["job_id"] = job_id
    results["completed_at"] = datetime.now(timezone.utc).isoformat()
    results["dataset_info"]["target_column"] = config["target_column"]
    results["dataset_info"]["protected_attributes"] = config["protected_attributes"]
    storage.write_json(job_id, "results.json", results, bucket="results")
    set_status(job_id, "generating_explanation", "Generating AI explanation...")

    await asyncio.sleep(2)
    explanation = dict(MOCK_EXPLANATION)
    explanation["job_id"] = job_id
    explanation["generated_at"] = datetime.now(timezone.utc).isoformat()
    storage.write_json(job_id, "explanation.json", explanation, bucket="results")
    set_status(job_id, "generating_report", "Building audit report...")

    await asyncio.sleep(1)
    set_status(job_id, "complete", "Audit complete! Dashboard is ready.")


# ── POST /analyze/configure ───────────────────────────────────────────────────

@router.post("/analyze/configure")
async def configure_job(req: ConfigureRequest, background_tasks: BackgroundTasks):
    """
    Validates configuration and kicks off the analysis pipeline.
    Returns immediately; poll /status/{job_id} for progress.
    """
    # Special demo job
    is_demo = req.job_id == "demo"

    if not is_demo:
        # Verify CSV was uploaded
        if not storage.file_exists(req.job_id, "data.csv", bucket="uploads"):
            raise HTTPException(
                status_code=404,
                detail=f"No CSV found for job_id={req.job_id}. Upload a CSV first.",
            )

    if not req.target_column:
        raise HTTPException(status_code=400, detail="target_column is required.")
    if not req.protected_attributes:
        raise HTTPException(status_code=400, detail="At least one protected_attribute is required.")

    config = {
        "job_id": req.job_id,
        "dataset_path": f"fairlens-uploads/{req.job_id}/data.csv",
        "model_path": f"fairlens-uploads/{req.job_id}/model.pkl",
        "predictions_path": f"fairlens-uploads/{req.job_id}/predictions.csv",
        "target_column": req.target_column,
        "protected_attributes": req.protected_attributes,
        "positive_outcome_label": req.positive_outcome_label,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    if is_demo:
        # Seed demo data and simulate pipeline
        _seed_demo_job()
        background_tasks.add_task(_run_analysis_or_mock, "demo", config)
    else:
        background_tasks.add_task(_run_pipeline, req.job_id, config)

    return JSONResponse({"job_id": req.job_id, "status": "queued"})


def _seed_demo_job():
    """Pre-seed the demo job with mock results so it completes quickly."""
    from mocks.mock_data import MOCK_RESULTS, MOCK_EXPLANATION

    job_id = "demo"
    set_status(job_id, "uploading", "Loading demo dataset...")

    results = dict(MOCK_RESULTS)
    results["job_id"] = job_id
    storage.write_json(job_id, "results.json", results, bucket="results")

    explanation = dict(MOCK_EXPLANATION)
    explanation["job_id"] = job_id
    storage.write_json(job_id, "explanation.json", explanation, bucket="results")


# ── GET /status/{job_id} ──────────────────────────────────────────────────────

@router.get("/status/{job_id}")
async def get_job_status(job_id: str):
    """Returns the current status.json for this job."""
    return JSONResponse(get_status(job_id))
