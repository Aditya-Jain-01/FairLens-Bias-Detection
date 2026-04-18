"""
routers/remediate.py
Bias remediation endpoints + results retrieval.

POST /api/v1/remediate/reweigh   — applies reweighing and returns updated results
GET  /api/v1/remediate/threshold — computes metrics at a given threshold (< 200ms)
GET  /api/v1/results/{job_id}    — returns results.json
"""

import sys
import time
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

import pandas as pd

# Add ml/ to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "ml"))

from services import storage

logger = logging.getLogger(__name__)

router = APIRouter()


# ─────────────────────────────────────────────
# REQUEST / RESPONSE SCHEMAS
# ─────────────────────────────────────────────

class ReweighRequest(BaseModel):
    job_id: str


class ThresholdResponse(BaseModel):
    threshold: float
    accuracy: float
    per_group: dict
    demographic_parity_difference: float
    equalized_odds_difference: float
    latency_ms: Optional[float] = Field(None, description="Internal: how long this took in ms")


# ─────────────────────────────────────────────
# STORAGE HELPERS
# ─────────────────────────────────────────────

def _load_predictions(job_id: str) -> pd.DataFrame:
    """
    Load predictions.csv for a job from storage or in-memory cache.

    Args:
        job_id: Job UUID string.

    Returns:
        DataFrame with y_true, y_pred_proba, y_pred, + protected attrs.
    """
    from ml.remediation import _PREDICTIONS_CACHE, cache_predictions

    if job_id in _PREDICTIONS_CACHE:
        return _PREDICTIONS_CACHE[job_id]

    # Try storage
    try:
        pred_path = storage.get_local_file_path(job_id, "predictions.csv", bucket="uploads")
        if pred_path.exists():
            df = pd.read_csv(pred_path)
            cache_predictions(job_id, df)
            return df
    except Exception:
        pass

    raise FileNotFoundError(
        f"predictions.csv not found for job_id={job_id}. "
        "Run /analyze/configure first."
    )


def _load_results(job_id: str) -> dict:
    """Load results.json from storage."""
    if storage.file_exists(job_id, "results.json", bucket="results"):
        return storage.read_json(job_id, "results.json", bucket="results")
    raise FileNotFoundError(f"results.json not found for job_id={job_id}")


def _save_results(job_id: str, results: dict) -> None:
    """Persist updated results.json back to storage."""
    storage.write_json(job_id, "results.json", results, bucket="results")


# ─────────────────────────────────────────────
# GET /results/{job_id}
# ─────────────────────────────────────────────

@router.get("/results/{job_id}")
async def get_results(job_id: str) -> dict:
    """
    GET /api/v1/results/{job_id}

    Returns results.json for a completed job.
    """
    if storage.file_exists(job_id, "results.json", bucket="results"):
        return storage.read_json(job_id, "results.json", bucket="results")

    raise HTTPException(
        status_code=404,
        detail=f"Results not found for job_id={job_id}. Has the analysis completed?",
    )


# ─────────────────────────────────────────────
# POST /remediate/reweigh
# ─────────────────────────────────────────────

@router.post("/remediate/reweigh")
async def reweigh(request: ReweighRequest) -> dict:
    """
    POST /api/v1/remediate/reweigh

    Applies reweighing transformation and returns an updated results block.
    Reweighing reweights training instances to remove discrimination.
    """
    job_id = request.job_id

    try:
        results = _load_results(job_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Results not found for job_id={job_id}. Run /analyze/configure first.",
        )

    try:
        pred_df = _load_predictions(job_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Extract config from results
    dataset_info = results.get("dataset_info", {})
    target_col = dataset_info.get("target_column", "income")
    protected_attrs = dataset_info.get("protected_attributes", ["sex"])
    primary_attr = protected_attrs[0]

    # Detect privileged group
    from ml.bias_engine import _detect_privileged
    privileged_val = _detect_privileged(pred_df, "y_true", primary_attr)

    # Build a DataFrame suitable for reweighing
    df_for_reweigh = pred_df.rename(columns={"y_true": target_col, "y_pred": "y_pred"})

    # Load data.csv for feature columns
    try:
        data_path = storage.get_local_file_path(job_id, "data.csv", bucket="uploads")
        data_df = pd.read_csv(data_path)

        if "income" in data_df.columns and pd.api.types.is_string_dtype(data_df["income"]):
            data_df["income"] = (
                data_df["income"].str.strip().apply(lambda x: 1 if ">50K" in str(x) else 0)
            )
        data_df["y_pred"] = pred_df["y_pred"].values
        feature_cols = [
            c for c in data_df.columns
            if c not in [target_col, "y_pred", "y_pred_proba"] + protected_attrs
        ]

        from ml.remediation import run_reweighing_pipeline
        reweigh_result = run_reweighing_pipeline(
            df=data_df,
            target_col=target_col,
            protected_col=primary_attr,
            privileged_value=privileged_val,
            feature_cols=feature_cols,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Reweighing failed: {str(e)}",
        )

    # Update results.remediation.reweighing
    results.setdefault("remediation", {})
    results["remediation"]["reweighing"] = reweigh_result

    _save_results(job_id, results)
    return results


# ─────────────────────────────────────────────
# GET /remediate/threshold
# ─────────────────────────────────────────────

@router.get("/remediate/threshold", response_model=ThresholdResponse)
async def get_threshold_metrics(
    job_id: str = Query(..., description="Job UUID"),
    threshold: float = Query(0.5, ge=0.0, le=1.0, description="Decision threshold"),
    protected: str = Query("sex", description="Protected attribute column name"),
) -> ThresholdResponse:
    """
    GET /api/v1/remediate/threshold?job_id=x&threshold=0.6&protected=sex

    Recomputes fairness metrics at a given classification threshold.
    Uses in-memory cache for sub-200ms response time.
    """
    start = time.perf_counter()

    try:
        pred_df = _load_predictions(job_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    if protected not in pred_df.columns:
        raise HTTPException(
            status_code=422,
            detail=f"Protected attribute '{protected}' not found in predictions.csv. "
                   f"Available columns: {list(pred_df.columns)}",
        )

    if "y_pred_proba" not in pred_df.columns:
        raise HTTPException(
            status_code=422,
            detail="predictions.csv must contain 'y_pred_proba' column for threshold calibration.",
        )

    from ml.remediation import compute_threshold_metrics
    result = compute_threshold_metrics(
        job_id=job_id,
        threshold=threshold,
        protected_col=protected,
    )

    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
    result["latency_ms"] = elapsed_ms

    if elapsed_ms > 200:
        logger.warning(f"Threshold endpoint exceeded 200ms: {elapsed_ms}ms for job={job_id}")

    return ThresholdResponse(**result)
