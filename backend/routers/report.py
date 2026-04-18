"""
routers/report.py
PDF Report Generation and Download.

GET /api/v1/report/{job_id} — Generate PDF audit report and return download URL
"""

import os
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from services import storage
from services.status import set_status

logger = logging.getLogger(__name__)

router = APIRouter()


# ── GET /report/{job_id} ──────────────────────────────────────────────────────

@router.get("/report/{job_id}")
async def get_report(job_id: str):
    """
    Generate a PDF audit report for a completed job.

    Flow:
      1. Read results.json + explanation.json from storage
      2. Generate PDF via WeasyPrint from Jinja2 template
      3. Save PDF to storage as results/{job_id}/report.pdf
      4. Update status.json → "complete"
      5. Return download URL

    If PDF already exists, returns the download URL directly.
    """
    # Check if report already exists
    if storage.file_exists(job_id, "report.pdf", bucket="results"):
        use_local = os.getenv("USE_LOCAL_STORAGE", "true").lower() == "true"
        if use_local:
            download_url = f"/storage_local/results/{job_id}/report.pdf"
        else:
            from services.gcs import get_signed_url
            results_bucket = os.getenv("GCS_RESULTS_BUCKET", "fairlens-results")
            download_url = get_signed_url(
                bucket=results_bucket,
                blob_path=f"{job_id}/report.pdf",
            )
        return {
            "download_url": download_url,
            "job_id": job_id,
            "message": "Report is ready.",
        }

    # 1. Load data files
    try:
        results = storage.read_json(job_id, "results.json", bucket="results")
    except Exception:
        raise HTTPException(status_code=404, detail=f"results.json not found for job {job_id}")

    try:
        explanation = storage.read_json(job_id, "explanation.json", bucket="results")
    except Exception:
        raise HTTPException(
            status_code=404,
            detail=f"explanation.json not found for job {job_id}. Run /explain first.",
        )

    # 2. Generate PDF
    try:
        from services.pdf_generator import generate_pdf_report
        logger.info(f"Generating PDF for job {job_id}")
        pdf_bytes = generate_pdf_report(results=results, explanation=explanation)
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="PDF generation not available — install weasyprint and Jinja2.",
        )
    except Exception as exc:
        logger.error(f"PDF generation failed for job {job_id}: {exc}")
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {exc}")

    # 3. Save to storage
    try:
        storage.write_bytes(job_id, "report.pdf", pdf_bytes, bucket="results")
        logger.info(f"report.pdf saved for job {job_id} ({len(pdf_bytes):,} bytes)")
    except Exception as exc:
        logger.error(f"Failed to save report.pdf for job {job_id}: {exc}")
        raise HTTPException(status_code=500, detail=f"Failed to save PDF: {exc}")

    set_status(job_id, "complete", "Audit report ready.")

    # 5. Return download URL
    use_local = os.getenv("USE_LOCAL_STORAGE", "true").lower() == "true"
    if use_local:
        download_url = f"/storage_local/results/{job_id}/report.pdf"
    else:
        from services.gcs import get_signed_url
        results_bucket = os.getenv("GCS_RESULTS_BUCKET", "fairlens-results")
        download_url = get_signed_url(
            bucket=results_bucket,
            blob_path=f"{job_id}/report.pdf",
            expiration_seconds=3600,
        )

    return {
        "download_url": download_url,
        "job_id": job_id,
        "expires_in_seconds": 3600,
    }
