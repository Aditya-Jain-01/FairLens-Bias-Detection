"""
services/db.py
Phase 2.2 — Firestore job metadata database.

When GCP_PROJECT_ID is set, job status and results are persisted to Firestore
in addition to the existing local JSON files (which act as a read cache).

When not set (local dev without GCP credentials), all calls are no-ops so
the system degrades gracefully to the existing JSON-file behaviour.

Collection: "jobs"
Document ID: job_id (UUID string)

Document schema:
{
    "id":         str,
    "created_at": datetime,
    "updated_at": datetime,
    "stage":      str,        # "uploading" | "configuring" | ... | "complete" | "error"
    "progress":   int,        # 0–100
    "message":    str,
    "error":      str | None,
    "config":     dict | None,
    "results":    dict | None,
}
"""

import os
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

_PROJECT = os.getenv("GCP_PROJECT_ID", "")
_client = None   # lazy-initialised singleton


def _get_client():
    """Return the Firestore client, initialising it on first call."""
    global _client
    if _client is not None:
        return _client
    if not _PROJECT:
        return None
    try:
        from google.cloud import firestore
        _client = firestore.Client(project=_PROJECT)
        logger.info("Firestore client initialised.")
        return _client
    except Exception as exc:
        logger.warning(f"Firestore init failed: {exc} — DB features disabled.")
        return None


def _jobs_collection():
    """Return the Firestore 'jobs' collection reference, or None."""
    client = _get_client()
    return client.collection("jobs") if client else None


# ── Write helpers ─────────────────────────────────────────────────────────────

def db_set_status(
    job_id: str,
    stage: str,
    message: str = "",
    progress: int = 0,
    error: Optional[str] = None,
) -> None:
    """Upsert job status fields in Firestore."""
    col = _jobs_collection()
    if col is None:
        return
    try:
        now = datetime.now(timezone.utc)
        data: Dict[str, Any] = {
            "id":         job_id,
            "stage":      stage,
            "message":    message,
            "progress":   progress,
            "updated_at": now,
        }
        if error is not None:
            data["error"] = error
        # Only stamp created_at on first status write (uploading = job creation)
        if stage == "uploading":
            data["created_at"] = now
        # merge=True so we don't overwrite config/results on status updates
        col.document(job_id).set(data, merge=True)
    except Exception as exc:
        logger.warning(f"db_set_status failed for {job_id}: {exc}")


def db_upsert_config(job_id: str, config: dict) -> None:
    """Persist job configuration to Firestore."""
    col = _jobs_collection()
    if col is None:
        return
    try:
        col.document(job_id).set({"config": config}, merge=True)
    except Exception as exc:
        logger.warning(f"db_upsert_config failed for {job_id}: {exc}")


def db_upsert_results(job_id: str, results: dict) -> None:
    """Persist full results payload to Firestore."""
    col = _jobs_collection()
    if col is None:
        return
    try:
        col.document(job_id).set({"results": results}, merge=True)
    except Exception as exc:
        logger.warning(f"db_upsert_results failed for {job_id}: {exc}")


# ── Read helpers ──────────────────────────────────────────────────────────────

def db_get_status(job_id: str) -> Optional[Dict[str, Any]]:
    """Return the status fields for a job, or None if not found / Firestore unavailable."""
    col = _jobs_collection()
    if col is None:
        return None
    try:
        doc = col.document(job_id).get()
        if not doc.exists:
            return None
        data = doc.to_dict()
        return {
            "job_id":   job_id,
            "stage":    data.get("stage", "unknown"),
            "progress": data.get("progress", 0),
            "message":  data.get("message", ""),
            "error":    data.get("error"),
        }
    except Exception as exc:
        logger.warning(f"db_get_status failed for {job_id}: {exc}")
        return None


def db_get_results(job_id: str) -> Optional[dict]:
    """Return results dict for a job, or None."""
    col = _jobs_collection()
    if col is None:
        return None
    try:
        doc = col.document(job_id).get()
        if not doc.exists:
            return None
        return doc.to_dict().get("results")
    except Exception as exc:
        logger.warning(f"db_get_results failed for {job_id}: {exc}")
        return None


def db_list_jobs(limit: int = 50) -> List[Dict[str, Any]]:
    """Return a list of recent jobs, newest first."""
    col = _jobs_collection()
    if col is None:
        return []
    try:
        from google.cloud import firestore as _fs
        docs = (
            col
            .order_by("created_at", direction=_fs.Query.DESCENDING)
            .limit(limit)
            .stream()
        )
        results = []
        for doc in docs:
            data = doc.to_dict()
            results.append({
                "job_id":     data.get("id", doc.id),
                "stage":      data.get("stage", "unknown"),
                "progress":   data.get("progress", 0),
                "message":    data.get("message", ""),
                "created_at": data.get("created_at", "").isoformat()
                              if hasattr(data.get("created_at", ""), "isoformat") else "",
                "config":     data.get("config", {}),
            })
        return results
    except Exception as exc:
        logger.warning(f"db_list_jobs failed: {exc}")
        return []
