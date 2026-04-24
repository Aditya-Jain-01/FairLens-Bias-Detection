"""
routers/report.py
PDF Report Generation and Download.

GET /api/v1/report/{job_id}
  — Generates PDF, saves to storage, returns {"download_url": "/api/v1/report/{job_id}/pdf"}

GET /api/v1/report/{job_id}/pdf
  — Streams PDF bytes directly from storage (works locally AND on GCS).
    This avoids the need for GCS signed URLs or public bucket permissions.

The frontend (api.ts downloadReport) opens download_url in a new tab.
The browser receives application/pdf and the PDF downloads normally.
"""

import logging
import os

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import Response

from services import storage
from services.status import set_status
from services.auth import require_api_key
from services.audit_logger import log_event, read_log

logger = logging.getLogger(__name__)

router = APIRouter()


# ── GET /report/{job_id}/pdf ──────────────────────────────────────────────────

@router.get("/report/{job_id}/pdf", dependencies=[Depends(require_api_key)])
async def stream_report_pdf(job_id: str):
    """
    Stream the PDF report bytes for a job directly from storage.

    Works in both local and GCS mode — the storage layer handles
    the download from GCS to a temp file transparently.

    Called by the frontend after /report/{job_id} returns download_url.
    """
    if not storage.file_exists(job_id, "report.pdf", bucket="results"):
        raise HTTPException(
            status_code=404,
            detail=f"report.pdf not found for job {job_id}. Call GET /report/{job_id} first."
        )
    try:
        pdf_path = storage.get_local_file_path(job_id, "report.pdf", bucket="results")
        pdf_bytes = pdf_path.read_bytes()
    except Exception as exc:
        logger.error(f"Failed to read report.pdf for job {job_id}: {exc}")
        raise HTTPException(status_code=500, detail=f"Could not read report: {exc}")

    log_event(job_id, "report_downloaded")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="fairlens_report_{job_id[:8]}.pdf"'},
    )


# ── GET /report/{job_id} ──────────────────────────────────────────────────────

@router.get("/report/{job_id}", dependencies=[Depends(require_api_key)])
async def get_report(job_id: str):
    """
    Generate (or retrieve cached) PDF audit report.

    Returns JSON: { "download_url": "/api/v1/report/{job_id}/pdf" }

    The returned URL is a backend proxy endpoint that streams the PDF
    directly — no GCS signed URLs or public bucket permissions required.

    Flow:
      1. If report.pdf already in storage, return its download URL immediately.
      2. Otherwise: load results.json + explanation.json, generate PDF,
         save to storage, update status, return download URL.
    """
    download_url = f"/api/v1/report/{job_id}/pdf"

    # 1. Return cached PDF URL if already generated
    if storage.file_exists(job_id, "report.pdf", bucket="results"):
        return {"download_url": download_url}

    # 2. Load results
    try:
        results = storage.read_json(job_id, "results.json", bucket="results")
    except Exception:
        raise HTTPException(status_code=404, detail=f"results.json not found for job {job_id}")

    # 3. Load explanation (PDF can still be generated without it)
    try:
        explanation = storage.read_json(job_id, "explanation.json", bucket="results")
    except Exception:
        logger.warning(f"explanation.json not found for job {job_id} — using placeholder.")
        from datetime import datetime, timezone
        explanation = {
            "job_id": job_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": "Explanation not yet available.",
            "severity_label": results.get("overall_severity", "unknown").title() + " bias detected",
            "findings": [],
            "recommended_fix": "none",
            "recommended_fix_reason": "",
            "plain_english": "AI explanation was not available at the time this report was generated.",
        }

    # 4. Generate PDF
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

    # 5. Persist to storage
    try:
        storage.write_bytes(job_id, "report.pdf", pdf_bytes, bucket="results")
        logger.info(f"report.pdf saved for job {job_id} ({len(pdf_bytes):,} bytes)")
    except Exception as exc:
        logger.warning(f"Could not persist report.pdf: {exc}")

    set_status(job_id, "complete", "Audit report ready.")
    log_event(job_id, "report_generated", detail={"size_bytes": len(pdf_bytes)})

    # 6. Return the download URL
    return {"download_url": download_url}


# ── GET /audit-log/{job_id} ───────────────────────────────────────────────────

@router.get("/audit-log/{job_id}", dependencies=[Depends(require_api_key)])
async def get_audit_log(job_id: str):
    """
    GET /api/v1/audit-log/{job_id}

    Returns the full chronological access log for this job.
    Each entry: {ts, event, job_id, ip, detail}
    Entries are returned newest-first.
    """
    return {"job_id": job_id, "events": read_log(job_id)}
