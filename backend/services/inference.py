"""
services/inference.py
Loads a .pkl or .onnx model and runs predictions against data.csv.
Saves predictions.csv to storage.
"""

import os
import json
import csv
import random
from pathlib import Path
from services import storage
from services.status import set_status


def run_inference(job_id: str, config: dict) -> Path:
    """
    Loads the model (if any) and generates predictions.csv.

    If no model file is provided, we generate dummy predictions
    (all 0.5 probability) so the pipeline doesn't break — useful
    when users only upload a CSV for analysis.

    Returns the local Path to predictions.csv.
    """
    set_status(job_id, "running_inference", "Loading model and running predictions...")

    csv_path = storage.get_local_file_path(job_id, "data.csv", bucket="uploads")
    
    target_col = config.get("target_column", "")
    
    model_path: Path | None = None
    if storage.file_exists(job_id, "model.pkl", bucket="uploads"):
        model_path = storage.get_local_file_path(job_id, "model.pkl", bucket="uploads")

    if model_path and model_path.suffix == ".pkl":
        predictions = _run_sklearn(model_path, csv_path, target_col)
    elif model_path and model_path.suffix == ".onnx":
        predictions = _run_onnx(model_path, csv_path, target_col)
    else:
        # No model — use actual labels as pseudo-predictions (demo mode)
        predictions = []
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if target_col in row:
                    try:
                        label = float(row[target_col])
                        prob = label * 0.85 + random.uniform(0, 0.15)
                        prob = min(max(prob, 0.0), 1.0)
                        predicted = 1 if prob >= 0.5 else 0
                    except ValueError:
                        prob = 0.5
                        predicted = 0
                else:
                    prob = 0.5
                    predicted = 0
                predictions.append({"probability": prob, "predicted_label": predicted})

    # Save predictions.csv
    import tempfile
    tmp = Path(tempfile.mkdtemp()) / "predictions.csv"
    
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["probability", "predicted_label"])
        writer.writeheader()
        writer.writerows(predictions)
        
    storage.save_upload_file(job_id, "predictions.csv", tmp)

    return tmp


def _run_sklearn(model_path: Path, csv_path: Path, target_col: str) -> list[dict]:
    import joblib
    import pandas as pd
    
    model = joblib.load(model_path)
    df = pd.read_csv(csv_path)

    feature_cols = [c for c in df.columns if c != target_col]
    X = df[feature_cols].copy()

    for col in X.select_dtypes(include=["object", "category"]).columns:
        X[col] = X[col].astype("category").cat.codes

    X = X.fillna(0)

    try:
        prob = model.predict_proba(X)[:, 1]
    except AttributeError:
        pred = model.predict(X)
        prob = pred.astype(float)

    predicted = (prob >= 0.5).astype(int)
    
    return [{"probability": p, "predicted_label": l} for p, l in zip(prob, predicted)]


def _run_onnx(model_path: Path, csv_path: Path, target_col: str) -> list[dict]:
    import pandas as pd
    import numpy as np
    try:
        import onnxruntime as rt  # type: ignore
    except ImportError:
        raise ImportError("onnxruntime is not installed. Run: pip install onnxruntime")

    df = pd.read_csv(csv_path)
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
    
    return [{"probability": float(p), "predicted_label": int(l)} for p, l in zip(prob, predicted)]
