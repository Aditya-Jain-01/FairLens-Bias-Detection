"""
services/gcs.py — GCS Adapter

Thin adapter that delegates to services/storage.py,
which handles local vs GCP mode transparently.
"""

import json
import os
from pathlib import Path
from services import storage

RESULTS_BUCKET = os.getenv("GCS_RESULTS_BUCKET", "fairlens-results")
UPLOAD_BUCKET = os.getenv("GCS_UPLOAD_BUCKET", "fairlens-uploads")


def _job_id_from_path(blob_path: str) -> str:
    """Extract job_id from e.g. '3f7a1b2c/results.json'"""
    return blob_path.split("/")[0]


def _filename_from_path(blob_path: str) -> str:
    """Extract filename from e.g. '3f7a1b2c/results.json'"""
    return blob_path.split("/")[-1]


def _resolve_bucket(bucket: str) -> str:
    """Map GCS bucket name to 'results' or 'uploads' key."""
    if bucket == RESULTS_BUCKET:
        return "results"
    return "uploads"


def read_json(bucket: str, blob_path: str) -> dict:
    """Read a JSON file from storage."""
    job_id = _job_id_from_path(blob_path)
    filename = _filename_from_path(blob_path)
    b = _resolve_bucket(bucket)
    return storage.read_json(job_id, filename, bucket=b)


def write_json(bucket: str, blob_path: str, data: dict) -> None:
    """Write a dict as JSON to storage."""
    job_id = _job_id_from_path(blob_path)
    filename = _filename_from_path(blob_path)
    b = _resolve_bucket(bucket)
    storage.write_json(job_id, filename, data, bucket=b)


def write_bytes(
    bucket: str,
    blob_path: str,
    data: bytes,
    content_type: str = "application/octet-stream",
) -> None:
    """Write raw bytes to storage (e.g. PDF files)."""
    job_id = _job_id_from_path(blob_path)
    filename = _filename_from_path(blob_path)
    b = _resolve_bucket(bucket)
    storage.write_bytes(job_id, filename, data, bucket=b)


def get_signed_url(
    bucket: str,
    blob_path: str,
    expiration_seconds: int = 3600,
) -> str:
    """
    Return a URL for downloading the file.

    In local mode: returns a relative path the frontend can hit directly
    via the StaticFiles mount.
    In GCP mode: delegates to google-cloud-storage signed URL generation.
    """
    job_id = _job_id_from_path(blob_path)
    filename = _filename_from_path(blob_path)
    use_local = os.getenv("USE_LOCAL_STORAGE", "true").lower() == "true"

    if use_local:
        return f"/storage_local/results/{job_id}/{filename}"

    # GCP: delegate to google-cloud-storage signed URL
    from google.cloud import storage as gcs_lib
    import datetime

    client = gcs_lib.Client()
    blob = client.bucket(bucket).blob(blob_path)
    return blob.generate_signed_url(
        expiration=datetime.timedelta(seconds=expiration_seconds),
        method="GET",
    )
