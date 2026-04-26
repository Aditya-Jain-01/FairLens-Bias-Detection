"""
services/status.py
Centralises all status read/write for job lifecycle tracking.

Phase 2.2: Writes to Firestore (when GCP_PROJECT_ID is set) AND the local
status.json file. Reads prefer Firestore, falling back to the JSON file.
"""

from datetime import datetime, timezone
from typing import Optional
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
    error: Optional[str] = None,
    progress: Optional[int] = None,
) -> dict:
    if stage not in VALID_STAGES:
        raise ValueError(f"Invalid stage: {stage}")

    resolved_progress = progress if progress is not None else STAGE_PROGRESS[stage]
    data = {
        "job_id":     job_id,
        "stage":      stage,
        "progress":   resolved_progress,
        "message":    message or stage.replace("_", " ").title(),
        "error":      error,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    # Always write local JSON (fast, cheap, works offline)
    write_json(job_id, "status.json", data, bucket="uploads")

    # Also write to Firestore when available (for cross-instance consistency)
    try:
        from services.db import db_set_status
        db_set_status(job_id, stage, data["message"], resolved_progress, error)
    except Exception:
        pass  # Firestore failure must never break the pipeline

    return data


def get_status(job_id: str) -> dict:
    # Try Firestore first (authoritative when Cloud Tasks worker ran on a different instance)
    try:
        from services.db import db_get_status
        db_result = db_get_status(job_id)
        if db_result:
            db_result["updated_at"] = datetime.now(timezone.utc).isoformat()
            return db_result
    except Exception:
        pass

    # Fall back to local JSON file
    try:
        return read_json(job_id, "status.json", bucket="uploads")
    except FileNotFoundError:
        return {
            "job_id":     job_id,
            "stage":      "error",
            "progress":   0,
            "message":    "Job not found",
            "error":      f"No job found with id {job_id}",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
