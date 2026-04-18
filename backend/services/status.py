"""
services/status.py
Centralises all status.json read/write for job lifecycle tracking.
"""

from datetime import datetime, timezone
from services.storage import write_json, read_json

VALID_STAGES = [
    "uploading",
    "configuring",
    "running_inference",
    "computing_metrics",
    "generating_explanation",
    "generating_report",
    "complete",
    "error",
]

STAGE_PROGRESS = {
    "uploading": 5,
    "configuring": 10,
    "running_inference": 30,
    "computing_metrics": 55,
    "generating_explanation": 75,
    "generating_report": 90,
    "complete": 100,
    "error": 0,
}


def set_status(
    job_id: str,
    stage: str,
    message: str = "",
    error: str | None = None,
    progress: int | None = None,
) -> dict:
    if stage not in VALID_STAGES:
        raise ValueError(f"Invalid stage: {stage}")

    data = {
        "job_id": job_id,
        "stage": stage,
        "progress": progress if progress is not None else STAGE_PROGRESS[stage],
        "message": message or stage.replace("_", " ").title(),
        "error": error,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(job_id, "status.json", data, bucket="uploads")
    return data


def get_status(job_id: str) -> dict:
    try:
        return read_json(job_id, "status.json", bucket="uploads")
    except FileNotFoundError:
        return {
            "job_id": job_id,
            "stage": "error",
            "progress": 0,
            "message": "Job not found",
            "error": f"No job found with id {job_id}",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
