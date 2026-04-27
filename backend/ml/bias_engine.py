"""
ml/bias_engine.py
FairLens — Bias Analysis Engine

Computes all 4 fairness metrics using AIF360 + fairlearn + pandas.
Returns a dict matching the results.json metrics + per_group_stats schema.

Usage:
    python ml/bias_engine.py --csv adult.csv --target income --protected sex,race
"""

import argparse
import json
import warnings
from datetime import datetime, timezone
from typing import Any, List

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")


# ─────────────────────────────────────────────
# METRIC HELPERS
# ─────────────────────────────────────────────

def _compute_disparate_impact(
    df: pd.DataFrame,
    target_col: str,
    protected_col: str,
    privileged_value: Any,
) -> float:
    """
    Compute Disparate Impact ratio.

    DI = P(Y=1 | unprivileged) / P(Y=1 | privileged)

    Args:
        df: DataFrame with ground-truth labels.
        target_col: Binary outcome column name (0/1).
        protected_col: Protected attribute column name.
        privileged_value: The value considered privileged (e.g., 'Male').

    Returns:
        Disparate impact ratio rounded to 3 decimal places.
    """
    priv = df[df[protected_col] == privileged_value][target_col].mean()
    unpriv = df[df[protected_col] != privileged_value][target_col].mean()
    if priv == 0:
        return 1.0
    return round(float(unpriv / priv), 3)


def _compute_demographic_parity_difference(
    df: pd.DataFrame,
    pred_col: str,
    protected_col: str,
    privileged_value: Any,
) -> float:
    """
    Compute Demographic Parity Difference.

    DPD = P(Ŷ=1 | unprivileged) - P(Ŷ=1 | privileged)

    Args:
        df: DataFrame with binary predictions.
        pred_col: Binary prediction column name (0/1).
        protected_col: Protected attribute column name.
        privileged_value: The value considered privileged.

    Returns:
        Demographic parity difference rounded to 3 decimal places.
    """
    try:
        from fairlearn.metrics import demographic_parity_difference
        dpd = demographic_parity_difference(
            y_true=df[pred_col],        # fairlearn accepts y_pred here too
            y_pred=df[pred_col],
            sensitive_features=df[protected_col],
        )
        return round(float(dpd), 3)
    except Exception:
        # Fallback: manual computation
        priv = df[df[protected_col] == privileged_value][pred_col].mean()
        unpriv = df[df[protected_col] != privileged_value][pred_col].mean()
        return round(float(unpriv - priv), 3)


def _compute_equalized_odds_difference(
    df: pd.DataFrame,
    target_col: str,
    pred_col: str,
    protected_col: str,
) -> float:
    """
    Compute Equalized Odds Difference using fairlearn.

    EOD = max(TPR_gap, FPR_gap) across groups.

    Args:
        df: DataFrame with true labels and binary predictions.
        target_col: Ground-truth binary label column.
        pred_col: Binary prediction column.
        protected_col: Protected attribute column.

    Returns:
        Equalized odds difference rounded to 3 decimal places.
    """
    try:
        from fairlearn.metrics import equalized_odds_difference
        eod = equalized_odds_difference(
            y_true=df[target_col],
            y_pred=df[pred_col],
            sensitive_features=df[protected_col],
        )
        return round(float(eod), 3)
    except Exception:
        # Fallback: manual max(TPR_gap, FPR_gap)
        groups = df[protected_col].unique()
        tprs, fprs = [], []
        for g in groups:
            sub = df[df[protected_col] == g]
            pos = sub[sub[target_col] == 1]
            neg = sub[sub[target_col] == 0]
            tpr = pos[pred_col].mean() if len(pos) > 0 else 0.0
            fpr = neg[pred_col].mean() if len(neg) > 0 else 0.0
            tprs.append(tpr)
            fprs.append(fpr)
        tpr_gap = max(tprs) - min(tprs)
        fpr_gap = max(fprs) - min(fprs)
        return round(float(max(tpr_gap, fpr_gap)), 3)


def _compute_calibration_difference(
    df: pd.DataFrame,
    target_col: str,
    pred_col: str,
    protected_col: str,
    privileged_value: Any,
) -> float:
    """
    Compute Calibration Difference (custom implementation).

    CALIB = |P(Y=1|Ŷ=1, unprivileged) - P(Y=1|Ŷ=1, privileged)|

    Args:
        df: DataFrame with true labels and binary predictions.
        target_col: Ground-truth binary label column.
        pred_col: Binary prediction column.
        protected_col: Protected attribute column.
        privileged_value: The value considered privileged.

    Returns:
        Calibration difference (absolute) rounded to 3 decimal places.
    """
    def _precision(sub):
        pred_pos = sub[sub[pred_col] == 1]
        if len(pred_pos) == 0:
            return 0.0
        return pred_pos[target_col].mean()

    priv_df = df[df[protected_col] == privileged_value]
    unpriv_df = df[df[protected_col] != privileged_value]
    diff = abs(_precision(unpriv_df) - _precision(priv_df))
    return round(float(diff), 3)


# ─────────────────────────────────────────────
# PER-GROUP STATS
# ─────────────────────────────────────────────

def _compute_per_group_stats(
    df: pd.DataFrame,
    target_col: str,
    pred_col: str,
    protected_col: str,
) -> dict:
    """
    Compute per-group count, positive_rate, TPR, FPR.

    Args:
        df: DataFrame with true labels and binary predictions.
        target_col: Ground-truth binary label column.
        pred_col: Binary prediction column.
        protected_col: Protected attribute column.

    Returns:
        Dict mapping group_value -> {count, positive_rate, tpr, fpr}
    """
    result = {}
    for group_val, sub in df.groupby(protected_col):
        count = len(sub)
        pos_rate = round(float(sub[target_col].mean()), 3)
        pos_mask = sub[target_col] == 1
        neg_mask = sub[target_col] == 0
        tpr = round(float(sub[pos_mask][pred_col].mean()), 3) if pos_mask.sum() > 0 else 0.0
        fpr = round(float(sub[neg_mask][pred_col].mean()), 3) if neg_mask.sum() > 0 else 0.0
        result[str(group_val)] = {
            "count": int(count),
            "positive_rate": pos_rate,
            "tpr": tpr,
            "fpr": fpr,
        }
    return result


# ─────────────────────────────────────────────
# SEVERITY CALCULATOR
# ─────────────────────────────────────────────

def _compute_severity(metrics: dict) -> str:
    """
    Compute overall bias severity from metrics dict.

    Rules:
        'high'   → 2+ metrics failed
        'medium' → exactly 1 metric failed
        'low'    → all passed but ≥1 value within 10% of threshold
        'none'   → all passed comfortably

    Args:
        metrics: Dict of metric_name -> {value, threshold, passed, ...}

    Returns:
        Severity string: 'high' | 'medium' | 'low' | 'none'
    """
    failed = sum(1 for m in metrics.values() if not m["passed"])
    if failed >= 2:
        return "high"
    if failed == 1:
        return "medium"

    # All passed — check if any are close to threshold (within 10%)
    for name, m in metrics.items():
        val = m["value"]
        threshold = m["threshold"]
        # Disparate impact: pass if val >= 0.8; close if val < 0.88
        if name == "disparate_impact":
            if val < threshold * 1.1:
                return "low"
        else:
            # Others: pass if abs(val) <= threshold; close if abs(val) > threshold * 0.9
            if abs(val) > threshold * 0.9:
                return "low"
    return "none"


# ─────────────────────────────────────────────
# PRIVILEGED VALUE DETECTION
# ─────────────────────────────────────────────

def _detect_privileged(df: pd.DataFrame, target_col: str, protected_col: str) -> Any:
    """
    Auto-detect the privileged group as the one with the highest positive outcome rate.

    Args:
        df: Input DataFrame.
        target_col: Ground-truth binary label column.
        protected_col: Protected attribute column.

    Returns:
        The group value with the highest positive rate.
    """
    return df.groupby(protected_col)[target_col].mean().idxmax()


# ─────────────────────────────────────────────
# MAIN PUBLIC FUNCTION
# ─────────────────────────────────────────────

def compute_bias_metrics(
    df: pd.DataFrame,
    target_col: str,
    protected_attributes: List[str],
    pred_col: str = "y_pred",
    job_id: str = "local-test",
) -> dict:
    """
    Compute all 4 fairness metrics + per_group_stats for a dataset.

    Expects df to contain:
        - target_col: ground-truth binary labels (0/1)
        - pred_col: binary predictions (0/1) — defaults to 'y_pred'
        - one column per protected attribute

    Args:
        df: DataFrame with labels, predictions, and protected attributes.
        target_col: Ground-truth binary outcome column name.
        protected_attributes: List of protected attribute column names.
        pred_col: Binary prediction column name.
        job_id: Job identifier for the output JSON.

    Returns:
        Dict matching the results.json metrics + per_group_stats + dataset_info schema.
    """
    if pred_col not in df.columns:
        raise ValueError(f"Prediction column '{pred_col}' not found. Available: {list(df.columns)}")

    # Use the first protected attribute as primary for scalar metrics
    primary_attr = protected_attributes[0]
    privileged_val = _detect_privileged(df, target_col, primary_attr)

    # ── 1. Disparate Impact (on ground truth)
    di_value = _compute_disparate_impact(df, target_col, primary_attr, privileged_val)
    di_threshold = 0.8
    di_passed = di_value >= di_threshold

    # ── 2. Demographic Parity Difference (on predictions)
    dpd_value = _compute_demographic_parity_difference(df, pred_col, primary_attr, privileged_val)
    dpd_threshold = 0.1
    dpd_passed = abs(dpd_value) <= dpd_threshold

    # ── 3. Equalized Odds Difference
    eod_value = _compute_equalized_odds_difference(df, target_col, pred_col, primary_attr)
    eod_threshold = 0.1
    eod_passed = abs(eod_value) <= eod_threshold

    # ── 4. Calibration Difference
    cal_value = _compute_calibration_difference(df, target_col, pred_col, primary_attr, privileged_val)
    cal_threshold = 0.1
    cal_passed = abs(cal_value) <= cal_threshold

    metrics = {
        "disparate_impact": {
            "value": di_value,
            "threshold": di_threshold,
            "passed": di_passed,
            "description": (
                "Ratio of positive outcome rate between unprivileged and privileged group. "
                "Must be >= 0.8 (80% rule)."
            ),
        },
        "demographic_parity_difference": {
            "value": dpd_value,
            "threshold": dpd_threshold,
            "passed": dpd_passed,
            "description": (
                "Difference in positive prediction rates between groups. "
                "Should be close to 0."
            ),
        },
        "equalized_odds_difference": {
            "value": eod_value,
            "threshold": eod_threshold,
            "passed": eod_passed,
            "description": (
                "Max difference in TPR/FPR between groups. "
                "Should be close to 0."
            ),
        },
        "calibration_difference": {
            "value": cal_value,
            "threshold": cal_threshold,
            "passed": cal_passed,
            "description": "Difference in score reliability (precision) across groups.",
        },
    }

    # ── Per-group stats for each protected attribute
    per_group_stats = {}
    for attr in protected_attributes:
        per_group_stats[attr] = _compute_per_group_stats(df, target_col, pred_col, attr)

    # ── Severity
    failed_count = sum(1 for m in metrics.values() if not m["passed"])
    passed_count = len(metrics) - failed_count
    severity = _compute_severity(metrics)

    # ── Dataset info
    pos_rate = round(float(df[target_col].mean()), 3)

    return {
        "job_id": job_id,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "dataset_info": {
            "total_rows": int(len(df)),
            "target_column": target_col,
            "protected_attributes": protected_attributes,
            "positive_rate_overall": pos_rate,
        },
        "metrics": metrics,
        "per_group_stats": per_group_stats,
        "overall_severity": severity,
        "metrics_passed": passed_count,
        "metrics_failed": failed_count,
    }


# ─────────────────────────────────────────────
# STANDALONE __main__ BLOCK
# ─────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FairLens Bias Engine")
    parser.add_argument("--csv", default=None, help="Path to local CSV file")
    parser.add_argument("--target", default="income", help="Target column name")
    parser.add_argument("--protected", default="sex,race", help="Comma-separated protected attributes")
    parser.add_argument("--pred", default="y_pred", help="Binary prediction column (if already in CSV)")
    args = parser.parse_args()

    protected_attrs = [p.strip() for p in args.protected.split(",")]

    # ── Load dataset
    if args.csv:
        print(f"Loading dataset from {args.csv}...")
        df = pd.read_csv(args.csv)
    else:
        print("Downloading Adult Income dataset from UCI...")
        columns = [
            "age", "workclass", "fnlwgt", "education", "education_num",
            "marital_status", "occupation", "relationship", "race", "sex",
            "capital_gain", "capital_loss", "hours_per_week", "native_country", "income",
        ]
        url = "https://archive.ics.uci.edu/ml/machine-learning-databases/adult/adult.data"
        df = pd.read_csv(url, names=columns, skipinitialspace=True)
        print(f"Loaded {len(df)} rows.")

    # ── Clean income label
    if "income" in df.columns and pd.api.types.is_string_dtype(df["income"]):
        df["income"] = df["income"].str.strip().apply(lambda x: 1 if ">50K" in str(x) else 0)

    # ── Generate predictions if not present
    if args.pred not in df.columns:
        print("No prediction column found — training a quick LogisticRegression for demo...")
        from sklearn.linear_model import LogisticRegression
        from sklearn.preprocessing import LabelEncoder

        feature_cols = [c for c in df.columns if c not in [args.target] + protected_attrs]
        X = df[feature_cols].copy()

        # Encode categoricals
        for col in X.select_dtypes(include=["object", "string"]).columns:
            X[col] = LabelEncoder().fit_transform(X[col].astype(str))

        X = X.fillna(0)
        y = df[args.target]

        clf = LogisticRegression(max_iter=1000, random_state=42)
        clf.fit(X, y)
        df["y_pred"] = clf.predict(X)
        print("Predictions generated.")

    # ── Run bias engine
    print("\nComputing fairness metrics...")
    result = compute_bias_metrics(
        df=df,
        target_col=args.target,
        protected_attributes=protected_attrs,
        pred_col=args.pred if args.pred in df.columns else "y_pred",
        job_id="local-test-001",
    )

    print("\n=== RESULTS ===")
    print(json.dumps(result, indent=2))

    # Save to file
    with open("results_partial.json", "w") as f:
        json.dump(result, f, indent=2)
    print("\n✓ Saved to results_partial.json")
