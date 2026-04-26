"""
services/queue.py
Phase 2.1 — Async Job Queue via Google Cloud Tasks.

When CLOUD_TASKS_QUEUE is set, jobs are dispatched to a Cloud Tasks queue
which calls POST /internal/run-job on this same Cloud Run service.

When the env var is NOT set (local dev), returns False so the caller
falls back to the current FastAPI BackgroundTasks behaviour.
"""

import json
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_QUEUE    = os.getenv("CLOUD_TASKS_QUEUE", "")          # e.g. "fairlens-jobs"
_LOCATION = os.getenv("CLOUD_TASKS_LOCATION", "us-central1")
_PROJECT  = os.getenv("GCP_PROJECT_ID", "")
_WORKER   = os.getenv("WORKER_URL", "")                 # full URL of /internal/run-job
_SECRET   = os.getenv("INTERNAL_WORKER_SECRET", "")


def enqueue_job(job_id: str, config: dict) -> bool:
    """
    Enqueue a bias analysis job to Cloud Tasks.

    Returns True if the task was successfully enqueued, False if Cloud Tasks
    is not configured (triggers in-process BackgroundTasks fallback).
    """
    if not all([_QUEUE, _PROJECT, _WORKER, _SECRET]):
        logger.info(
            "CLOUD_TASKS_QUEUE / WORKER_URL not set — falling back to in-process execution."
        )
        return False

    try:
        from google.cloud import tasks_v2

        client = tasks_v2.CloudTasksClient()
        parent = client.queue_path(_PROJECT, _LOCATION, _QUEUE)

        payload = json.dumps({"job_id": job_id, "config": config}).encode("utf-8")

        task = {
            "http_request": {
                "http_method": tasks_v2.HttpMethod.POST,
                "url": _WORKER,
                "headers": {
                    "Content-Type": "application/json",
                    "X-Internal-Secret": _SECRET,
                },
                "body": payload,
            }
        }

        response = client.create_task(request={"parent": parent, "task": task})
        logger.info(f"Enqueued job {job_id} to Cloud Tasks: {response.name}")
        return True

    except Exception as exc:
        logger.error(f"Cloud Tasks enqueue failed for job {job_id}: {exc} — falling back to in-process.")
        return False
