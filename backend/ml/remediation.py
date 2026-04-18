"""
ml/remediation.py
FairLens — Bias Remediation Engine (Person 2)

Implements:
  1. Reweighing transform (AIF360) — adjusts sample weights to reduce bias
  2. Threshold calibration calculator — fast per-threshold metric recomputation

Usage:
    python ml/remediation.py --preds ./artifacts/predictions.csv --protected sex
"""

import argparse
import json
import warnings
from functools import lru_cache
from typing import Any

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")


# ─────────────────────────────────────────────
# 1. REWEIGHING
# ─────────────────────────────────────────────

def apply_reweighing(
    df: pd.DataFrame,
    target_col: str,
    protected_col: str,
    privileged_value: Any,
) -> tuple[np.ndarray, dict]:
    """
    Compute sample weights using AIF360 Reweighing algorithm.

    Reweighing reweights training instances to remove discrimination before
    training. This function returns weights + the expected metrics_after block.

    Args:
        df: DataFrame with true labels and protected attribute.
        target_col: Binary outcome column (0/1).
        protected_col: Protected attribute column name.
        privileged_value: Value of the privileged group (e.g., 'Male').

    Returns:
        Tuple of (sample_weights array, reweighing_info dict)
    """
    try:
        from aif360.datasets import BinaryLabelDataset
        from aif360.algorithms.preprocessing import Reweighing as AIF360Reweighing

        # Build AIF360 dataset
        df_aif = df[[protected_col, target_col]].copy()
        df_aif[protected_col] = (df_aif[protected_col] == privileged_value).astype(int)

        dataset = BinaryLabelDataset(
            df=df_aif,
            label_names=[target_col],
            protected_attribute_names=[protected_col],
            privileged_protected_attributes=[[1]],
        )

        rw = AIF360Reweighing(
            privileged_groups=[{protected_col: 1}],
            unprivileged_groups=[{protected_col: 0}],
        )
        rw.fit(dataset)
        transformed = rw.transform(dataset)
        weights = transformed.instance_weights
        method = "aif360"

    except Exception as e:
        # Fallback: manual reweighing formula
        # w = P(Y) * P(A) / P(Y, A)
        weights = _manual_reweigh(df, target_col, protected_col, privileged_value)
        method = "manual"

    return weights, method


def _manual_reweigh(
    df: pd.DataFrame,
    target_col: str,
    protected_col: str,
    privileged_value: Any,
) -> np.ndarray:
    """
    Manual reweighing: w_i = P(Y=y_i) * P(A=a_i) / P(Y=y_i, A=a_i)

    Args:
        df: Input DataFrame.
        target_col: Binary target column.
        protected_col: Protected attribute column.
        privileged_value: Privileged group value.

    Returns:
        NumPy array of sample weights.
    """
    n = len(df)
    weights = np.ones(n)
    p_y = {v: (df[target_col] == v).mean() for v in [0, 1]}
    p_a_map = {privileged_value: (df[protected_col] == privileged_value).mean()}
    unpriv_vals = [v for v in df[protected_col].unique() if v != privileged_value]
    for v in unpriv_vals:
        p_a_map[v] = (df[protected_col] == v).mean()

    for i, row in df.iterrows():
        y_val = int(row[target_col])
        a_val = row[protected_col]
        p_y_val = p_y[y_val]
        p_a_val = p_a_map.get(a_val, 1.0)
        p_ya = ((df[target_col] == y_val) & (df[protected_col] == a_val)).mean()
        if p_ya > 0:
            weights[df.index.get_loc(i)] = (p_y_val * p_a_val) / p_ya

    return weights


def run_reweighing_pipeline(
    df: pd.DataFrame,
    target_col: str,
    protected_col: str,
    privileged_value: Any,
    feature_cols: list[str],
) -> dict:
    """
    Full reweighing pipeline: compute weights, retrain, measure metrics_after.

    Args:
        df: DataFrame with features, target, and protected attribute.
        target_col: Binary outcome column.
        protected_col: Protected attribute column.
        privileged_value: Privileged group value.
        feature_cols: Columns to use as features for retraining.

    Returns:
        Dict matching the 'remediation.reweighing' block in results.json.
    """
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import LabelEncoder

    # Original accuracy (no reweighing)
    X = df[feature_cols].copy()
    for col in X.select_dtypes(include=["object", "string"]).columns:
        X[col] = LabelEncoder().fit_transform(X[col].astype(str))
    X = X.fillna(0)
    y = df[target_col]

    clf_before = LogisticRegression(max_iter=1000, random_state=42)
    clf_before.fit(X, y)
    preds_before = clf_before.predict(X)
    accuracy_before = round(float((preds_before == y.values).mean()), 3)

    # Compute reweighing weights
    weights, method = apply_reweighing(df, target_col, protected_col, privileged_value)

    # Retrain with weights
    clf_after = LogisticRegression(max_iter=1000, random_state=42)
    clf_after.fit(X, y, sample_weight=weights)
    preds_after = clf_after.predict(X)
    accuracy_after = round(float((preds_after == y.values).mean()), 3)

    # Metrics after reweighing
    df_after = df.copy()
    df_after["y_pred"] = preds_after

    from bias_engine import (
        _compute_disparate_impact,
        _compute_demographic_parity_difference,
        _compute_equalized_odds_difference,
        _compute_calibration_difference,
    )

    di_after = _compute_disparate_impact(df_after, target_col, protected_col, privileged_value)
    dpd_after = _compute_demographic_parity_difference(df_after, "y_pred", protected_col, privileged_value)
    eod_after = _compute_equalized_odds_difference(df_after, target_col, "y_pred", protected_col)
    cal_after = _compute_calibration_difference(df_after, target_col, "y_pred", protected_col, privileged_value)

    return {
        "applied": True,
        "method": method,
        "metrics_after": {
            "disparate_impact": {
                "value": di_after,
                "passed": di_after >= 0.8,
            },
            "demographic_parity_difference": {
                "value": dpd_after,
                "passed": abs(dpd_after) <= 0.1,
            },
            "equalized_odds_difference": {
                "value": eod_after,
                "passed": abs(eod_after) <= 0.1,
            },
            "calibration_difference": {
                "value": cal_after,
                "passed": abs(cal_after) <= 0.1,
            },
        },
        "accuracy_before": accuracy_before,
        "accuracy_after": accuracy_after,
        "accuracy_delta": round(accuracy_after - accuracy_before, 3),
    }


# ─────────────────────────────────────────────
# 2. THRESHOLD CALIBRATION (< 200ms)
# ─────────────────────────────────────────────

# In-memory predictions cache: job_id -> DataFrame
_PREDICTIONS_CACHE: dict[str, pd.DataFrame] = {}


def cache_predictions(job_id: str, pred_df: pd.DataFrame) -> None:
    """
    Cache predictions DataFrame in memory for a given job_id.

    Args:
        job_id: Unique job identifier.
        pred_df: DataFrame with columns y_true, y_pred_proba, y_pred, + protected attrs.
    """
    _PREDICTIONS_CACHE[job_id] = pred_df


def load_predictions_cached(job_id: str, csv_path: str | None = None) -> pd.DataFrame:
    """
    Load predictions from cache or CSV file.

    Args:
        job_id: Job identifier.
        csv_path: Path to predictions.csv if not yet cached.

    Returns:
        DataFrame with prediction data.

    Raises:
        FileNotFoundError: If not cached and no CSV path given.
    """
    if job_id in _PREDICTIONS_CACHE:
        return _PREDICTIONS_CACHE[job_id]
    if csv_path:
        df = pd.read_csv(csv_path)
        _PREDICTIONS_CACHE[job_id] = df
        return df
    raise FileNotFoundError(f"No predictions cached for job_id={job_id} and no CSV path given.")


def compute_threshold_metrics(
    job_id: str,
    threshold: float,
    protected_col: str = "sex",
    csv_path: str | None = None,
) -> dict:
    """
    Recompute fairness metrics at a given classification threshold.

    Designed to respond in < 200ms by operating on cached DataFrames.

    Args:
        job_id: Job identifier (used for cache lookup).
        threshold: Decision threshold to apply to y_pred_proba.
        protected_col: Protected attribute column in predictions.csv.
        csv_path: Optional CSV path if predictions not yet cached.

    Returns:
        Dict matching the threshold endpoint response schema:
        {threshold, accuracy, per_group: {group: {tpr, fpr, positive_rate}},
         demographic_parity_difference, equalized_odds_difference}
    """
    pred_df = load_predictions_cached(job_id, csv_path)

    # Apply threshold
    pred_df = pred_df.copy()
    pred_df["y_pred_thresh"] = (pred_df["y_pred_proba"] >= threshold).astype(int)

    accuracy = round(float((pred_df["y_pred_thresh"] == pred_df["y_true"]).mean()), 3)

    per_group = {}
    groups = pred_df[protected_col].unique()

    group_pos_rates = []
    group_tprs = []

    for group_val in sorted(groups):
        sub = pred_df[pred_df[protected_col] == group_val]
        pos_mask = sub["y_true"] == 1
        neg_mask = sub["y_true"] == 0

        tpr = round(float(sub[pos_mask]["y_pred_thresh"].mean()), 3) if pos_mask.sum() > 0 else 0.0
        fpr = round(float(sub[neg_mask]["y_pred_thresh"].mean()), 3) if neg_mask.sum() > 0 else 0.0
        positive_rate = round(float(sub["y_pred_thresh"].mean()), 3)

        per_group[str(group_val)] = {
            "tpr": tpr,
            "fpr": fpr,
            "positive_rate": positive_rate,
        }
        group_pos_rates.append(positive_rate)
        group_tprs.append(tpr)

    # Scalar fairness metrics at this threshold
    dpd = round(float(min(group_pos_rates) - max(group_pos_rates)), 3)

    # Equalized odds: max gap in TPR across groups
    eod = round(float(max(group_tprs) - min(group_tprs)), 3)

    return {
        "threshold": round(threshold, 3),
        "accuracy": accuracy,
        "per_group": per_group,
        "demographic_parity_difference": dpd,
        "equalized_odds_difference": eod,
    }


# ─────────────────────────────────────────────
# STANDALONE __main__
# ─────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FairLens Remediation Engine")
    parser.add_argument("--preds", default="./artifacts/predictions.csv", help="Path to predictions.csv")
    parser.add_argument("--protected", default="sex", help="Primary protected attribute column")
    parser.add_argument("--threshold", type=float, default=0.5, help="Threshold to test")
    parser.add_argument("--job", default="local-test-001", help="Job ID for cache")
    args = parser.parse_args()

    print(f"Loading predictions from {args.preds}...")
    pred_df = pd.read_csv(args.preds)
    cache_predictions(args.job, pred_df)

    print(f"\nComputing metrics at threshold={args.threshold}...")
    result = compute_threshold_metrics(
        job_id=args.job,
        threshold=args.threshold,
        protected_col=args.protected,
        csv_path=args.preds,
    )

    print("\n=== THRESHOLD RESULT ===")
    print(json.dumps(result, indent=2))

    # Test a sweep of thresholds
    print("\n=== THRESHOLD SWEEP ===")
    for t in [0.3, 0.4, 0.5, 0.6, 0.7]:
        r = compute_threshold_metrics(args.job, t, args.protected)
        print(f"  t={t}: accuracy={r['accuracy']}, dpd={r['demographic_parity_difference']}, eod={r['equalized_odds_difference']}")
