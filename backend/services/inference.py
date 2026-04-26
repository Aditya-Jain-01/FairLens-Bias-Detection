"""
services/inference.py
Loads a .pkl or .onnx model and runs predictions against data.csv.
Saves predictions.csv to storage with all columns needed downstream:
  y_pred_proba, y_pred, y_true, + all protected attribute columns.
"""


import tempfile
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from services import storage
from services.status import set_status


def run_inference(job_id: str, config: dict) -> Path:
    """
    Loads the model (if any) and generates predictions.csv.

    predictions.csv schema:
        y_pred_proba    — predicted probability (float 0-1)
        y_pred          — binary prediction (0 or 1)
        y_true          — ground-truth label from data.csv
        <protected_attr> — one column per protected attribute

    If no model file is provided, pseudo-predictions are generated from
    the ground-truth labels (useful for CSV-only bias analysis).
    """
    set_status(job_id, "running_inference", "Loading model and running predictions...")

    csv_path = storage.get_local_file_path(job_id, "data.csv", bucket="uploads")
    target_col = config.get("target_column", "")
    protected_attrs = config.get("protected_attributes", [])

    # Load raw data once — used for y_true and protected attr extraction
    raw_df = pd.read_csv(csv_path)

    # Normalise binary target (handle ">50K" style string labels)
    if target_col and target_col in raw_df.columns:
        col = raw_df[target_col]
        if pd.api.types.is_string_dtype(col):
            raw_df[target_col] = col.str.strip().apply(
                lambda x: 1 if (">50K" in str(x) or str(x).strip() == "1") else 0
            )
        else:
            raw_df[target_col] = pd.to_numeric(col, errors="coerce").fillna(0).astype(int)

    # ── Run model inference ──────────────────────────────────────────────────
    model_path: Optional[Path] = None
    if storage.file_exists(job_id, "model.pkl", bucket="uploads"):
        model_path = storage.get_local_file_path(job_id, "model.pkl", bucket="uploads")

    if model_path and model_path.suffix == ".pkl":
        preds = _run_sklearn(model_path, raw_df.copy(), target_col)
    elif model_path and model_path.suffix == ".onnx":
        preds = _run_onnx(model_path, raw_df.copy(), target_col)
    else:
        # No model — derive pseudo-predictions from ground-truth labels
        preds = _pseudo_predictions(raw_df, target_col)

    # ── Build final predictions DataFrame ────────────────────────────────────
    pred_df = pd.DataFrame(preds)

    # Attach ground-truth labels
    if target_col and target_col in raw_df.columns:
        pred_df["y_true"] = raw_df[target_col].values
    else:
        pred_df["y_true"] = pred_df["y_pred"].values  # fallback

    # Attach protected attribute columns (needed for threshold calibration)
    for attr in protected_attrs:
        if attr in raw_df.columns:
            pred_df[attr] = raw_df[attr].values

    # ── Save predictions.csv ─────────────────────────────────────────────────
    tmp = Path(tempfile.mkdtemp()) / "predictions.csv"
    pred_df.to_csv(tmp, index=False)
    storage.save_upload_file(job_id, "predictions.csv", tmp)

    return tmp


# ── Inference helpers ─────────────────────────────────────────────────────────

def _pseudo_predictions(df: pd.DataFrame, target_col: str) -> List[Dict]:
    """Generate pseudo-predictions from ground-truth labels (no model mode)."""
    import numpy as np

    if target_col and target_col in df.columns:
        labels = pd.to_numeric(df[target_col], errors="coerce").fillna(0).values.astype(float)
        # Add small random noise so the pseudo probabilities aren't all 0/1
        noise = np.random.default_rng(42).uniform(0, 0.15, size=len(labels))
        probs = np.clip(labels * 0.85 + noise, 0.0, 1.0)
    else:
        probs = np.full(len(df), 0.5)

    predicted = (probs >= 0.5).astype(int)
    return [
        {"y_pred_proba": float(p), "y_pred": int(l)}
        for p, l in zip(probs, predicted)
    ]



def _run_sklearn(model_path: Path, df: pd.DataFrame, target_col: str) -> List[Dict]:
    """Run a scikit-learn .pkl model and return predictions."""
    import joblib

    model = joblib.load(model_path)
    feature_cols = [c for c in df.columns if c != target_col]
    X = df[feature_cols].copy()

    # Encode remaining categoricals (in case model expects encoded input)
    for col in X.select_dtypes(include=["object", "category"]).columns:
        X[col] = X[col].astype("category").cat.codes

    X = X.fillna(0)

    try:
        prob = model.predict_proba(X)[:, 1]
    except AttributeError:
        pred = model.predict(X)
        prob = pred.astype(float)

    predicted = (prob >= 0.5).astype(int)
    return [{"y_pred_proba": float(p), "y_pred": int(l)} for p, l in zip(prob, predicted)]


def _run_onnx(model_path: Path, df: pd.DataFrame, target_col: str) -> List[Dict]:
    """Run an ONNX model and return predictions."""
    import numpy as np
    try:
        import onnxruntime as rt  # type: ignore
    except ImportError:
        raise ImportError("onnxruntime is not installed. Run: pip install onnxruntime")

    feature_cols = [c for c in df.columns if c != target_col]
    X = df[feature_cols].copy()
    for col in X.select_dtypes(include=["object", "category"]).columns:
        X[col] = X[col].astype("category").cat.codes
    X = X.fillna(0).astype(np.float32)

    sess = rt.InferenceSession(str(model_path))
    input_name = sess.get_inputs()[0].name
    result = sess.run(None, {input_name: X.values})

    prob = result[1][:, 1] if len(result) > 1 else result[0].flatten()
    predicted = (prob >= 0.5).astype(int)
    return [{"y_pred_proba": float(p), "y_pred": int(l)} for p, l in zip(prob, predicted)]
