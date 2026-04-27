"""
routers/upload.py
Handles CSV and model file uploads.

POST /api/v1/upload/csv
POST /api/v1/upload/model
"""

import uuid
import tempfile
from pathlib import Path

import shutil
from contextlib import asynccontextmanager

import pandas as pd
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import JSONResponse

from services import storage
from services.csv_parser import parse_csv
from services.status import set_status
from services.auth import require_api_key
from services.pii_detector import detect_pii
from services.audit_logger import log_event

router = APIRouter()

ALLOWED_MODEL_EXTENSIONS = {".pkl", ".onnx"}
MAX_CSV_SIZE_MB = 200
MAX_MODEL_SIZE_MB = 500


# ── helpers ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def _save_temp(upload: UploadFile):
    """Stream an UploadFile to a local temp file and yield its Path. Cleans up automatically."""
    suffix = Path(upload.filename or "file").suffix
    tmp_dir = Path(tempfile.mkdtemp())
    tmp_path = tmp_dir / f"upload{suffix}"
    try:
        with open(tmp_path, "wb") as f:
            while chunk := await upload.read(1024 * 1024):  # 1 MB chunks
                f.write(chunk)
        yield tmp_path
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ── POST /upload/csv ──────────────────────────────────────────────────────────

@router.post("/upload/csv", dependencies=[Depends(require_api_key)])
async def upload_csv(file: UploadFile = File(...)):
    """
    Accepts a CSV file.
    Returns: { job_id, columns, row_count }
    """
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are accepted.")

    # Generate a fresh job_id
    job_id = str(uuid.uuid4())

    # Save to temp, validate, then persist to storage
    try:
        async with _save_temp(file) as tmp_path:
            # Check file size
            size_mb = tmp_path.stat().st_size / (1024 * 1024)
            if size_mb > MAX_CSV_SIZE_MB:
                raise HTTPException(status_code=413, detail=f"CSV too large ({size_mb:.1f} MB). Max is {MAX_CSV_SIZE_MB} MB.")

            # Parse columns
            try:
                info = parse_csv(tmp_path)
            except ValueError as e:
                raise HTTPException(status_code=422, detail=str(e))

            # PII detection (scan column names + 5 sample values per column)
            pii_result = {"has_pii": False, "flagged_columns": []}
            try:
                df_sample = pd.read_csv(tmp_path, nrows=5)
                sample_values = {col: df_sample[col].dropna().tolist() for col in df_sample.columns}
                pii_result = detect_pii(info["columns"], sample_values)
            except Exception:
                pass  # PII detection is best-effort — never block the upload

            # Persist to storage
            try:
                storage.save_upload_file(job_id, "data.csv", tmp_path)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Storage error: {e}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process uploaded file: {e}")

    # Set initial status (best-effort)
    try:
        set_status(job_id, "uploading", "CSV uploaded, waiting for configuration.")
    except Exception:
        pass

    # Audit log
    log_event(job_id, "upload_csv", detail={
        "filename": file.filename,
        "row_count": info["row_count"],
        "columns": len(info["columns"]),
        "pii_detected": pii_result["has_pii"],
    })

    return JSONResponse({
        "job_id": job_id,
        "columns": info["columns"],
        "row_count": info["row_count"],
        "pii_scan": pii_result,
    })


# ── POST /upload/model ────────────────────────────────────────────────────────

@router.post("/upload/model", dependencies=[Depends(require_api_key)])
async def upload_model(
    file: UploadFile = File(...),
    job_id: str = Form(...),
):
    """
    Accepts a .pkl or .onnx model file.
    Must include job_id (from the CSV upload step).
    Returns: { job_id, model_type }
    """
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_MODEL_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Only {', '.join(ALLOWED_MODEL_EXTENSIONS)} model files are accepted.",
        )

    try:
        async with _save_temp(file) as tmp_path:
            size_mb = tmp_path.stat().st_size / (1024 * 1024)
            if size_mb > MAX_MODEL_SIZE_MB:
                raise HTTPException(status_code=413, detail=f"Model file too large ({size_mb:.1f} MB). Max is {MAX_MODEL_SIZE_MB} MB.")

            try:
                storage.save_upload_file(job_id, "model.pkl" if suffix == ".pkl" else "model.onnx", tmp_path)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Storage error: {e}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process uploaded file: {e}")

    model_type = "sklearn" if suffix == ".pkl" else "onnx"

    return JSONResponse({
        "job_id": job_id,
        "model_type": model_type,
    })
