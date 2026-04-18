"""
services/analysis_pipeline.py — Unified Bias Analysis Pipeline

Core analysis service that integrates bias detection, SHAP attribution,
and remediation into a single pipeline callable from the background task runner.

This module:
1. Loads data.csv, predictions.csv, config.json from storage
2. Runs bias_engine + shap_engine + remediation
3. Writes results.json to storage
4. Updates status along the way
"""

import os
import sys
import logging
import pickle
import tempfile
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd

# Add ml/ to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "ml"))

from services import storage
from services.status import set_status

logger = logging.getLogger(__name__)




def run_full_analysis(job_id: str) -> dict:
    """
    Full bias analysis pipeline for a given job.

    Reads data.csv, predictions.csv, config.json from storage,
    runs bias_engine + shap_engine + remediation, writes results.json.

    Args:
        job_id: Job UUID string.

    Returns:
        Complete results dict matching CONTRACT.md results.json schema.
    """
    from ml.bias_engine import compute_bias_metrics, _detect_privileged
    from ml.shap_engine import compute_shap_values
    from ml.remediation import run_reweighing_pipeline, cache_predictions

    set_status(job_id, "computing_metrics", "Loading data and config...", progress=10)

    # ── Load config
    try:
        config = storage.read_json(job_id, "config.json", bucket="uploads")
    except FileNotFoundError:
        config = {
            "job_id": job_id,
            "target_column": "income",
            "protected_attributes": ["sex", "race"],
            "positive_outcome_label": 1,
        }

    target_col = config.get("target_column", "income")
    protected_attrs = config.get("protected_attributes", ["sex", "race"])

    # ── Load data
    csv_path = storage.get_local_file_path(job_id, "data.csv", bucket="uploads")
    df = pd.read_csv(csv_path)

    # Clean income label if needed (Adult Income dataset)
    if "income" in df.columns and pd.api.types.is_string_dtype(df["income"]):
        df["income"] = df["income"].str.strip().apply(lambda x: 1 if ">50K" in str(x) else 0)

    set_status(job_id, "computing_metrics", "Loading predictions...", progress=25)

    # ── Load predictions
    pred_path = storage.get_local_file_path(job_id, "predictions.csv", bucket="uploads")
    pred_df = pd.read_csv(pred_path)
    cache_predictions(job_id, pred_df)

    # Merge predictions into main df
    if "y_pred" in pred_df.columns and "y_pred" not in df.columns:
        df["y_pred"] = pred_df["y_pred"].values

    if "y_pred" not in df.columns:
        raise ValueError("No y_pred column found in data.csv or predictions.csv")

    set_status(job_id, "computing_metrics", "Computing fairness metrics...", progress=40)

    # ── Bias metrics
    bias_result = compute_bias_metrics(
        df=df,
        target_col=target_col,
        protected_attributes=protected_attrs,
        pred_col="y_pred",
        job_id=job_id,
    )

    set_status(job_id, "computing_metrics", "Computing SHAP attributions...", progress=60)

    # ── SHAP
    shap_block = {"top_features": [], "protected_attr_shap": {}, "note": "SHAP not computed"}
    try:
        pipeline = _load_model(job_id)
        if pipeline is not None:
            feature_cols = [c for c in df.columns if c not in [target_col, "y_pred", "y_pred_proba"]]
            X = df[feature_cols]
            prot_data = df[protected_attrs]
            shap_block = compute_shap_values(
                pipeline=pipeline,
                X=X,
                protected_attributes=protected_attrs,
                protected_col_data=prot_data,
            )
    except Exception as e:
        logger.warning(f"SHAP computation failed: {e}")

    set_status(job_id, "computing_metrics", "Running reweighing remediation...", progress=80)

    # ── Remediation
    primary_attr = protected_attrs[0]
    privileged_val = _detect_privileged(df, target_col, primary_attr)

    remediation_block = {
        "reweighing": {"applied": False},
        "threshold": {
            "current_threshold": 0.5,
            "privileged_group": str(privileged_val),
            "unprivileged_group": "other",
        },
    }

    try:
        feature_cols = [
            c for c in df.columns
            if c not in [target_col, "y_pred", "y_pred_proba"] + protected_attrs
        ]
        reweigh_result = run_reweighing_pipeline(
            df=df,
            target_col=target_col,
            protected_col=primary_attr,
            privileged_value=privileged_val,
            feature_cols=feature_cols,
        )
        remediation_block["reweighing"] = reweigh_result

        # Detect unprivileged group
        unpriv_groups = [
            g for g in df[primary_attr].unique() if g != privileged_val
        ]
        remediation_block["threshold"]["unprivileged_group"] = (
            str(unpriv_groups[0]) if unpriv_groups else "other"
        )
    except Exception as e:
        logger.warning(f"Reweighing failed: {e}")

    set_status(job_id, "computing_metrics", "Assembling results.json...", progress=95)

    # ── Assemble full results.json
    results = {
        **bias_result,
        "shap": shap_block,
        "remediation": remediation_block,
    }

    # Write to storage
    storage.write_json(job_id, "results.json", results, bucket="results")

    set_status(job_id, "generating_explanation", "Metrics complete — ready for AI explanation.")
    return results


def _load_model(job_id: str):
    """
    Load the model.pkl from storage.

    Returns the loaded sklearn pipeline, or None if no model exists.
    """
    try:
        if storage.file_exists(job_id, "model.pkl", bucket="uploads"):
            model_path = storage.get_local_file_path(job_id, "model.pkl", bucket="uploads")
            with open(model_path, "rb") as f:
                return pickle.load(f)
    except Exception as e:
        logger.warning(f"Could not load model.pkl for job {job_id}: {e}")
    return None
