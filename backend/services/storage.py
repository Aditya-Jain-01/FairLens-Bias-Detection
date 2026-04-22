"""
services/storage.py
Abstracts all file I/O so the rest of the code is identical
whether running locally or on GCP.

Set USE_LOCAL_STORAGE=true in .env to bypass GCS entirely.
"""

import os
import json
import shutil
from pathlib import Path
from typing import Union

USE_LOCAL = os.getenv("USE_LOCAL_STORAGE", "true").lower() == "true"
LOCAL_UPLOAD_DIR = Path(os.getenv("LOCAL_UPLOAD_DIR", "./storage_local/uploads"))
LOCAL_RESULTS_DIR = Path(os.getenv("LOCAL_RESULTS_DIR", "./storage_local/results"))


# ── helpers ──────────────────────────────────────────────────────────────────

def _upload_path(job_id: str) -> Path:
    p = LOCAL_UPLOAD_DIR / job_id
    p.mkdir(parents=True, exist_ok=True)
    return p

def _results_path(job_id: str) -> Path:
    p = LOCAL_RESULTS_DIR / job_id
    p.mkdir(parents=True, exist_ok=True)
    return p


# ── GCS helpers (imported lazily so the app starts without GCP creds) ────────

def _gcs_client():
    from google.cloud import storage  # type: ignore
    return storage.Client()

def _gcs_upload_blob(bucket_name: str, source_path: Path, destination_blob: str):
    client = _gcs_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(destination_blob)
    blob.upload_from_filename(str(source_path))

def _gcs_download_blob(bucket_name: str, blob_name: str, dest_path: Path):
    client = _gcs_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.download_to_filename(str(dest_path))

def _gcs_write_json(bucket_name: str, blob_name: str, data: dict):
    client = _gcs_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_string(json.dumps(data, indent=2), content_type="application/json")

def _gcs_read_json(bucket_name: str, blob_name: str) -> dict:
    client = _gcs_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    return json.loads(blob.download_as_text())


# ── Public API ────────────────────────────────────────────────────────────────

UPLOAD_BUCKET = os.getenv("GCS_UPLOAD_BUCKET", "fairlens-uploads")
RESULTS_BUCKET = os.getenv("GCS_RESULTS_BUCKET", "fairlens-results")


def save_upload_file(job_id: str, filename: str, source_path: Path) -> str:
    """Save an uploaded file. Returns the storage path/blob name."""
    if USE_LOCAL:
        dest = _upload_path(job_id) / filename
        shutil.copy2(source_path, dest)
        return str(dest)
    else:
        blob_name = f"{job_id}/{filename}"
        _gcs_upload_blob(UPLOAD_BUCKET, source_path, blob_name)
        return f"gs://{UPLOAD_BUCKET}/{blob_name}"


def write_json(job_id: str, filename: str, data: dict, bucket: str = "results") -> str:
    """Write a JSON file to results (or uploads) bucket."""
    if USE_LOCAL:
        if bucket == "results":
            dest = _results_path(job_id) / filename
        else:
            dest = _upload_path(job_id) / filename
        dest.write_text(json.dumps(data, indent=2))
        return str(dest)
    else:
        gcs_bucket = RESULTS_BUCKET if bucket == "results" else UPLOAD_BUCKET
        blob_name = f"{job_id}/{filename}"
        _gcs_write_json(gcs_bucket, blob_name, data)
        return f"gs://{gcs_bucket}/{blob_name}"


def write_bytes(job_id: str, filename: str, data: bytes, bucket: str = "results") -> str:
    """Write raw bytes to storage (e.g. PDF files)."""
    if USE_LOCAL:
        if bucket == "results":
            dest = _results_path(job_id) / filename
        else:
            dest = _upload_path(job_id) / filename
        dest.write_bytes(data)
        return str(dest)
    else:
        gcs_bucket = RESULTS_BUCKET if bucket == "results" else UPLOAD_BUCKET
        client = _gcs_client()
        blob = client.bucket(gcs_bucket).blob(f"{job_id}/{filename}")
        blob.upload_from_string(data)
        return f"gs://{gcs_bucket}/{job_id}/{filename}"


def read_json(job_id: str, filename: str, bucket: str = "results") -> dict:
    """Read a JSON file from storage."""
    if USE_LOCAL:
        if bucket == "results":
            p = _results_path(job_id) / filename
        else:
            p = _upload_path(job_id) / filename
        return json.loads(p.read_text())
    else:
        gcs_bucket = RESULTS_BUCKET if bucket == "results" else UPLOAD_BUCKET
        return _gcs_read_json(gcs_bucket, f"{job_id}/{filename}")


def file_exists(job_id: str, filename: str, bucket: str = "results") -> bool:
    if USE_LOCAL:
        if bucket == "results":
            return (_results_path(job_id) / filename).exists()
        else:
            return (_upload_path(job_id) / filename).exists()
    else:
        gcs_bucket = RESULTS_BUCKET if bucket == "results" else UPLOAD_BUCKET
        client = _gcs_client()
        b = client.bucket(gcs_bucket)
        return b.blob(f"{job_id}/{filename}").exists()


def get_local_file_path(job_id: str, filename: str, bucket: str = "uploads") -> Path:
    """Return a local Path for a file (copies from GCS first if needed)."""
    if USE_LOCAL:
        if bucket == "uploads":
            return _upload_path(job_id) / filename
        else:
            return _results_path(job_id) / filename
    else:
        # Download from GCS to a temp local path
        import tempfile
        tmp = Path(tempfile.mkdtemp()) / filename
        gcs_bucket = UPLOAD_BUCKET if bucket == "uploads" else RESULTS_BUCKET
        _gcs_download_blob(gcs_bucket, f"{job_id}/{filename}", tmp)
        return tmp


def list_jobs(bucket: str = "results") -> list:
    """List all job_id directories in the given bucket."""
    if USE_LOCAL:
        target_dir = LOCAL_RESULTS_DIR if bucket == "results" else LOCAL_UPLOAD_DIR
        if not target_dir.exists():
            return []
        return [d.name for d in target_dir.iterdir() if d.is_dir()]
    else:
        # GCP fallback (not required for local run)
        gcs_bucket = RESULTS_BUCKET if bucket == "results" else UPLOAD_BUCKET
        client = _gcs_client()
        blobs = client.list_blobs(gcs_bucket)
        prefixes = set(b.name.split("/")[0] for b in blobs if "/" in b.name)
        return list(prefixes)
