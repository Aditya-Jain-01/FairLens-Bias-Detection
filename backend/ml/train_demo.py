"""
ml/train_demo.py
FairLens — Demo Model Trainer (Person 2)

Trains a LogisticRegression on the Adult Income dataset.
Saves:
  - demo_model.pkl       (sklearn pipeline)
  - predictions.csv      (y_true, y_pred_proba, y_pred, sex, race)

Usage:
    python ml/train_demo.py [--out ./artifacts]
"""

import argparse
import os
import pickle
import warnings

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, OneHotEncoder, StandardScaler

warnings.filterwarnings("ignore")

COLUMNS = [
    "age", "workclass", "fnlwgt", "education", "education_num",
    "marital_status", "occupation", "relationship", "race", "sex",
    "capital_gain", "capital_loss", "hours_per_week", "native_country", "income",
]

PROTECTED_ATTRS = ["sex", "race"]
TARGET_COL = "income"

NUMERIC_FEATURES = [
    "age", "fnlwgt", "education_num", "capital_gain",
    "capital_loss", "hours_per_week",
]
CATEGORICAL_FEATURES = [
    "workclass", "education", "marital_status", "occupation",
    "relationship", "native_country",
]


def load_adult_data(csv_path: str | None = None) -> pd.DataFrame:
    """
    Load the Adult Income dataset from a local CSV or UCI URL.

    Args:
        csv_path: Optional path to a local CSV. If None, downloads from UCI.

    Returns:
        Cleaned DataFrame with binary 'income' column.
    """
    if csv_path and os.path.exists(csv_path):
        print(f"Loading from {csv_path}...")
        df = pd.read_csv(csv_path, names=COLUMNS, skipinitialspace=True)
    else:
        print("Downloading Adult Income dataset from UCI...")
        url = "https://archive.ics.uci.edu/ml/machine-learning-databases/adult/adult.data"
        df = pd.read_csv(url, names=COLUMNS, skipinitialspace=True)

    # Clean target
    df[TARGET_COL] = df[TARGET_COL].str.strip().apply(lambda x: 1 if ">50K" in str(x) else 0)

    # Strip whitespace from string columns
    for col in df.select_dtypes(include=["object", "string"]).columns:
        df[col] = df[col].str.strip()

    print(f"Loaded {len(df)} rows. Positive rate: {df[TARGET_COL].mean():.3f}")
    return df


def build_pipeline() -> Pipeline:
    """
    Build a sklearn Pipeline with preprocessing + LogisticRegression.

    Returns:
        Unfitted sklearn Pipeline.
    """
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), NUMERIC_FEATURES),
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL_FEATURES),
        ]
    )
    pipeline = Pipeline([
        ("preprocessor", preprocessor),
        ("classifier", LogisticRegression(max_iter=1000, random_state=42, C=1.0)),
    ])
    return pipeline


def train_and_save(csv_path: str | None = None, out_dir: str = ".") -> dict:
    """
    Train LogisticRegression on Adult Income and save artifacts.

    Args:
        csv_path: Optional local CSV path.
        out_dir: Directory to write demo_model.pkl and predictions.csv.

    Returns:
        Dict with accuracy, paths, and basic stats.
    """
    os.makedirs(out_dir, exist_ok=True)

    df = load_adult_data(csv_path)

    feature_cols = NUMERIC_FEATURES + CATEGORICAL_FEATURES
    X = df[feature_cols]
    y = df[TARGET_COL]

    print("Training LogisticRegression pipeline...")
    pipeline = build_pipeline()
    pipeline.fit(X, y)

    # Predictions
    y_pred = pipeline.predict(X)
    y_pred_proba = pipeline.predict_proba(X)[:, 1]
    accuracy = (y_pred == y).mean()
    print(f"Training accuracy: {accuracy:.4f}")

    # Save model
    model_path = os.path.join(out_dir, "demo_model.pkl")
    with open(model_path, "wb") as f:
        pickle.dump(pipeline, f)
    print(f"✓ Saved model to {model_path}")

    # Build predictions.csv — matches CONTRACT.md expectations
    # Columns: y_true, y_pred_proba, y_pred, + protected attributes
    pred_df = pd.DataFrame({
        "y_true": y.values,
        "y_pred_proba": np.round(y_pred_proba, 6),
        "y_pred": y_pred,
        "sex": df["sex"].values,
        "race": df["race"].values,
    })

    pred_path = os.path.join(out_dir, "predictions.csv")
    pred_df.to_csv(pred_path, index=False)
    print(f"✓ Saved predictions to {pred_path}")

    return {
        "accuracy": round(float(accuracy), 3),
        "model_path": model_path,
        "predictions_path": pred_path,
        "n_rows": len(df),
        "positive_rate": round(float(y.mean()), 3),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FairLens Demo Model Trainer")
    parser.add_argument("--csv", default=None, help="Path to local adult.csv (optional)")
    parser.add_argument("--out", default="./artifacts", help="Output directory")
    args = parser.parse_args()

    stats = train_and_save(csv_path=args.csv, out_dir=args.out)

    print("\n=== TRAINING COMPLETE ===")
    print(f"  Accuracy : {stats['accuracy']}")
    print(f"  Rows     : {stats['n_rows']}")
    print(f"  Pos rate : {stats['positive_rate']}")
    print(f"  Model    : {stats['model_path']}")
    print(f"  Preds    : {stats['predictions_path']}")
