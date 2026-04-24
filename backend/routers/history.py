from fastapi import APIRouter, Depends
from services import storage
from services.auth import require_api_key
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/history", dependencies=[Depends(require_api_key)])
async def get_history():
    """Returns all completed jobs, newest first."""
    jobs = storage.list_jobs(bucket="results")
    summaries = []
    
    for job_id in jobs:
        try:
            # Only consider jobs that have completed successfully
            if not storage.file_exists(job_id, "results.json", bucket="results"):
                continue
                
            r = storage.read_json(job_id, "results.json", bucket="results")
            
            summary = {
                "job_id": job_id,
                "completed_at": r.get("completed_at", ""),
                "dataset_info": r.get("dataset_info", {}),
                "overall_severity": r.get("overall_severity", "unknown"),
                "fairness_score": r.get("fairness_score", {}).get("score", 0),
                "metrics_passed": r.get("metrics_passed", 0),
                "metrics_failed": r.get("metrics_failed", 0),
            }
            summaries.append(summary)
        except Exception as e:
            logger.warning(f"Skipping history item for {job_id} due to error: {e}")
            continue
            
    # Sort descending by completion date
    return sorted(summaries, key=lambda x: x["completed_at"], reverse=True)
