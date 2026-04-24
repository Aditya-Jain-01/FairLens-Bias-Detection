"""
services/audit_logger.py
========================
Lightweight audit log for FairLens.

Appends one JSON-line per action to  storage_local/results/{job_id}/audit.log
(or GCS results bucket when USE_LOCAL_STORAGE=false).

Tracked events:
  - upload_csv       — file uploaded, columns returned
  - analysis_started — /analyze/configure called
  - explanation_read — /explain called
  - report_generated — PDF generated
  - report_downloaded — GET /report/{job_id}/pdf called
  - question_asked   — /ask called

Schema per line:
  {"ts": "ISO8601", "event": "...", "job_id": "...", "ip": "...", "detail": {...}}
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def _log_path(job_id: str) -> Path:
    results_dir = Path(os.getenv("LOCAL_RESULTS_DIR", "./storage_local/results"))
    job_dir = results_dir / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    return job_dir / "audit.log"


def log_event(job_id: str, event: str, ip: str = "unknown", detail: Optional[dict] = None) -> None:
    """
    Append one audit event to the job's audit.log file.
    Safe to call from any router — never raises.
    """
    try:
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "job_id": job_id,
            "ip": ip,
            "detail": detail or {},
        }
        with open(_log_path(job_id), "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as exc:
        logger.warning(f"Audit log write failed for job {job_id}: {exc}")


def read_log(job_id: str) -> list:
    """
    Read all audit events for a job. Returns newest-first list.
    Returns [] if log file doesn't exist yet.
    """
    path = _log_path(job_id)
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8").strip().splitlines()
        events = [json.loads(line) for line in lines if line.strip()]
        return list(reversed(events))  # newest first
    except Exception as exc:
        logger.warning(f"Audit log read failed for job {job_id}: {exc}")
        return []
