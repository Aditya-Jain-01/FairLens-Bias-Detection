"""
routers/report.py
PDF Report Generation and Download.

GET /api/v1/report/{job_id} — Generate PDF audit report and stream it directly.
"""

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from services import storage
from services.status import set_status

logger = logging.getLogger(__name__)

router = APIRouter()


# ── GET /report/{job_id} ──────────────────────────────────────────────────────

@router.get("/report/{job_id}")
async def get_report(job_id: str):
    """
    Generate (or retrieve cached) PDF audit report and stream it directly.

    Flow:
      1. If report.pdf already exists in storage, stream it immediately.
      2. Otherwise: read results.json + explanation.json, generate PDF,
         save to storage, update status, then stream the bytes.

    Returns the PDF as application/pdf — no signed URL needed.
    """
    # 1. Return cached PDF if available
    if storage.file_exists(job_id, "report.pdf", bucket="results"):
        try:
            pdf_path = storage.get_local_file_path(job_id, "report.pdf", bucket="results")
            pdf_bytes = pdf_path.read_bytes()
            return Response(
                content=pdf_bytes,
                media_type="application/pdf",
                headers={"Content-Disposition": f'attachment; filename="fairlens_report_{job_id[:8]}.pdf"'},
            )
        except Exception as exc:
            logger.warning(f"Could not read cached report: {exc} — regenerating.")

    # 2. Load results
    try:
        results = storage.read_json(job_id, "results.json", bucket="results")
    except Exception:
        raise HTTPException(status_code=404, detail=f"results.json not found for job {job_id}")

    # 3. Load explanation (best-effort — PDF can still be generated without it)
    try:
        explanation = storage.read_json(job_id, "explanation.json", bucket="results")
    except Exception:
        logger.warning(f"explanation.json not found for job {job_id} — using empty explanation.")
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

    # 5. Persist
    try:
        storage.write_bytes(job_id, "report.pdf", pdf_bytes, bucket="results")
        logger.info(f"report.pdf saved for job {job_id} ({len(pdf_bytes):,} bytes)")
    except Exception as exc:
        logger.warning(f"Could not persist report.pdf: {exc}")

    set_status(job_id, "complete", "Audit report ready.")

    # 6. Stream PDF directly — works identically locally and on Cloud Run
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="fairlens_report_{job_id[:8]}.pdf"'},
    )
