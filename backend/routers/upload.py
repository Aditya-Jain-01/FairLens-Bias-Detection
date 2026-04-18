"""
routers/upload.py
Handles CSV and model file uploads.

POST /api/v1/upload/csv
POST /api/v1/upload/model
"""

import uuid
import tempfile
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse

from services import storage
from services.csv_parser import parse_csv
from services.status import set_status

router = APIRouter()

ALLOWED_MODEL_EXTENSIONS = {".pkl", ".onnx"}
MAX_CSV_SIZE_MB = 200
MAX_MODEL_SIZE_MB = 500


# ── helpers ──────────────────────────────────────────────────────────────────

async def _save_temp(upload: UploadFile) -> Path:
    """Stream an UploadFile to a local temp file and return its Path."""
    suffix = Path(upload.filename or "file").suffix
    tmp = Path(tempfile.mkdtemp()) / f"upload{suffix}"
    with open(tmp, "wb") as f:
        while chunk := await upload.read(1024 * 1024):  # 1 MB chunks
            f.write(chunk)
    return tmp


# ── POST /upload/csv ──────────────────────────────────────────────────────────

@router.post("/upload/csv")
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
        tmp_path = await _save_temp(file)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read uploaded file: {e}")

    # Check file size
    size_mb = tmp_path.stat().st_size / (1024 * 1024)
    if size_mb > MAX_CSV_SIZE_MB:
        raise HTTPException(status_code=413, detail=f"CSV too large ({size_mb:.1f} MB). Max is {MAX_CSV_SIZE_MB} MB.")

    # Parse columns
    try:
        info = parse_csv(tmp_path)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # Persist to storage
    try:
        storage.save_upload_file(job_id, "data.csv", tmp_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Storage error: {e}")

    # Set initial status
    set_status(job_id, "uploading", "CSV uploaded, waiting for configuration.")

    return JSONResponse({
        "job_id": job_id,
        "columns": info["columns"],
        "row_count": info["row_count"],
    })


# ── POST /upload/model ────────────────────────────────────────────────────────

@router.post("/upload/model")
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
        tmp_path = await _save_temp(file)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read uploaded file: {e}")

    size_mb = tmp_path.stat().st_size / (1024 * 1024)
    if size_mb > MAX_MODEL_SIZE_MB:
        raise HTTPException(status_code=413, detail=f"Model file too large ({size_mb:.1f} MB). Max is {MAX_MODEL_SIZE_MB} MB.")

    try:
        storage.save_upload_file(job_id, "model.pkl" if suffix == ".pkl" else "model.onnx", tmp_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Storage error: {e}")

    model_type = "sklearn" if suffix == ".pkl" else "onnx"

    return JSONResponse({
        "job_id": job_id,
        "model_type": model_type,
    })
