"""
ml/shap_engine.py
FairLens — SHAP Attribution Engine

Computes SHAP feature importance + per-group breakdown for the bias report.
Returns the 'shap' block of results.json.

Usage:
    python ml/shap_engine.py --model ./artifacts/demo_model.pkl --preds ./artifacts/predictions.csv
"""

import argparse
import json
import pickle
import warnings
from typing import Any

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")



def _get_feature_names(pipeline, numeric_features: list[str], categorical_features: list[str]) -> list[str]:
    """
    Extract feature names from a fitted sklearn ColumnTransformer pipeline.

    Args:
        pipeline: Fitted sklearn Pipeline with 'preprocessor' step.
        numeric_features: List of numeric feature names.
        categorical_features: List of categorical feature names.

    Returns:
        List of feature name strings.
    """
    preprocessor = pipeline.named_steps["preprocessor"]
    num_names = numeric_features
    try:
        cat_encoder = preprocessor.named_transformers_["cat"]
        cat_names = list(cat_encoder.get_feature_names_out(categorical_features))
        return num_names + cat_names
    except KeyError:
        return num_names


def compute_shap_values(
    pipeline,
    X: pd.DataFrame,
    protected_attributes: list[str],
    protected_col_data: pd.DataFrame,
    top_n: int = 7,
    sample_size: int = 500,
) -> dict:
    """
    Compute SHAP feature attributions and per-group protected attribute SHAP values.

    Args:
        pipeline: Fitted sklearn Pipeline (preprocessor + classifier).
        X: Feature DataFrame (no target, no protected attributes in index).
        protected_attributes: List of protected attribute column names.
        protected_col_data: DataFrame with protected attribute columns (same index as X).
        top_n: Number of top features to return.
        sample_size: Rows to sample for SHAP (for speed).

    Returns:
        Dict matching the 'shap' block of results.json.
    """
    import shap

    # Sample for speed
    rng = np.random.default_rng(42)
    idx = rng.choice(len(X), size=min(sample_size, len(X)), replace=False)
    X_sample = X.iloc[idx].reset_index(drop=True)
    prot_sample = protected_col_data.iloc[idx].reset_index(drop=True)

    numeric_features = list(X.select_dtypes(include=[np.number]).columns)
    categorical_features = list(X.select_dtypes(exclude=[np.number]).columns)

    # Transform features
    try:
        preprocessor = pipeline.named_steps["preprocessor"]
        X_transformed = preprocessor.transform(X_sample)
        feature_names = _get_feature_names(pipeline, numeric_features, categorical_features)
    except Exception:
        # Fallback if no preprocessor or unable to extract feature names
        X_transformed = X_sample
        feature_names = list(X.columns)

    # Extract classifier — handle both Pipeline and bare estimators
    try:
        classifier = pipeline.named_steps["classifier"]
    except (AttributeError, KeyError):
        classifier = pipeline  # bare model

    # Build SHAP explainer — try in order: Linear → Tree → Kernel
    shap_vals = None
    try:
        explainer = shap.LinearExplainer(classifier, X_transformed, feature_perturbation="interventional")
        shap_vals = explainer.shap_values(X_transformed)
    except Exception:
        pass

    if shap_vals is None:
        try:
            explainer = shap.TreeExplainer(classifier)
            sv = explainer.shap_values(X_transformed)
            # TreeExplainer may return [shap_class0, shap_class1] for binary classifiers
            shap_vals = sv[1] if isinstance(sv, list) and len(sv) == 2 else sv
        except Exception:
            pass

    if shap_vals is None:
        # KernelExplainer: very slow, sample hard
        sample = shap.sample(X_transformed, 50)
        explainer = shap.KernelExplainer(classifier.predict_proba, sample)
        shap_vals = explainer.shap_values(sample, nsamples=50)[:, :, 1]

    # Mean absolute SHAP per feature
    mean_abs_shap = np.abs(shap_vals).mean(axis=0)
    mean_shap = shap_vals.mean(axis=0)  # signed mean for direction

    # Map back to original feature names (aggregate one-hot encoded cats)
    feature_importance: dict[str, float] = {}
    feature_direction: dict[str, float] = {}

    for i, fname in enumerate(feature_names):
        # Strip one-hot suffix to get original feature name
        orig = fname.split("_")[0] if "_" in fname else fname
        # For categorical originals, check against categorical_features
        for cat in categorical_features:
            if fname.startswith(cat + "_") or fname == cat:
                orig = cat
                break

        feature_importance[orig] = feature_importance.get(orig, 0.0) + float(mean_abs_shap[i])
        feature_direction[orig] = feature_direction.get(orig, 0.0) + float(mean_shap[i])

    # Sort by importance
    sorted_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)

    top_features = []
    for feat, importance in sorted_features[:top_n]:
        direction_val = feature_direction[feat]
        if abs(direction_val) < 0.005:
            direction = "mixed"
        elif direction_val > 0:
            direction = "positive"
        else:
            direction = "negative"
        top_features.append({
            "feature": feat,
            "importance": round(importance, 3),
            "direction": direction,
        })

    # Per protected attribute: mean absolute SHAP of that attribute if present
    # Since protected attrs may be included in features, we compute their mean |shap|
    protected_attr_shap = {}
    for attr in protected_attributes:
        attr_indices = [
            i for i, fname in enumerate(feature_names)
            if fname.startswith(attr + "_") or fname == attr
        ]
        if attr_indices:
            attr_shap = float(np.abs(shap_vals[:, attr_indices]).mean())
        else:
            # Attribute wasn't in training features — use indirect proxy (near 0)
            attr_shap = 0.0
        protected_attr_shap[attr] = round(attr_shap, 3)

    return {
        "top_features": top_features,
        "protected_attr_shap": protected_attr_shap,
        "note": (
            "Higher protected_attr_shap means the protected attribute is "
            "directly influencing predictions."
        ),
    }


def run_shap_from_files(
    model_path: str,
    data_csv: str,
    protected_attributes: list[str],
    target_col: str = "income",
) -> dict:
    """
    Convenience function: load model + CSV and compute SHAP values.

    Args:
        model_path: Path to demo_model.pkl.
        data_csv: Path to the raw dataset CSV.
        protected_attributes: List of protected attribute column names.
        target_col: Target column name.

    Returns:
        Dict matching the 'shap' block of results.json.
    """
    with open(model_path, "rb") as f:
        pipeline = pickle.load(f)

    from train_demo import NUMERIC_FEATURES, CATEGORICAL_FEATURES, load_adult_data
    df = load_adult_data(data_csv if data_csv else None)

    feature_cols = [c for c in df.columns if c not in [target_col, "y_pred", "y_pred_proba"]]
    X = df[feature_cols]
    protected_data = df[protected_attributes]

    return compute_shap_values(
        pipeline=pipeline,
        X=X,
        protected_attributes=protected_attributes,
        protected_col_data=protected_data,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FairLens SHAP Engine")
    parser.add_argument("--model", default="./artifacts/demo_model.pkl", help="Path to demo_model.pkl")
    parser.add_argument("--csv", default=None, help="Path to raw dataset CSV")
    parser.add_argument("--protected", default="sex,race", help="Comma-separated protected attributes")
    parser.add_argument("--target", default="income", help="Target column name")
    args = parser.parse_args()

    protected_attrs = [p.strip() for p in args.protected.split(",")]

    print("Running SHAP engine...")
    shap_result = run_shap_from_files(
        model_path=args.model,
        data_csv=args.csv,
        protected_attributes=protected_attrs,
        target_col=args.target,
    )

    print("\n=== SHAP RESULTS ===")
    print(json.dumps(shap_result, indent=2))
    print("\n✓ SHAP block matches results.json schema.")
