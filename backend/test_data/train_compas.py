"""
FairLens — Model trainer for COMPAS Recidivism Dataset
Upload output: model.pkl  +  compas_encoded.csv

Dataset source:
  https://github.com/propublica/compas-analysis/raw/master/compas-scores-two-years.csv

Usage:
  pip install pandas scikit-learn
  python train_compas.py

Then upload to FairLens:
  - CSV  → compas_encoded.csv
  - Model → model.pkl
  - Target column        → two_year_recid
  - Protected attributes → race, sex
  - Positive outcome     → 1  (re-offended = positive in bias analysis)
"""

import pickle
import urllib.request

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

# ── 1. Load ──────────────────────────────────────────────────────────────────
URL = "https://raw.githubusercontent.com/propublica/compas-analysis/master/compas-scores-two-years.csv"
print("Downloading COMPAS dataset...")
urllib.request.urlretrieve(URL, "compas_raw.csv")
df = pd.read_csv("compas_raw.csv")
print(f"  Loaded {len(df):,} rows, {df.shape[1]} columns")

# ── 2. Select & clean relevant columns ───────────────────────────────────────
KEEP = [
    "age", "age_cat",
    "race", "sex",
    "juv_fel_count", "juv_misd_count", "juv_other_count",
    "priors_count",
    "c_charge_degree",          # felony (F) vs misdemeanor (M)
    "decile_score",             # COMPAS risk score 1-10
    "score_text",               # Low / Medium / High
    "two_year_recid",           # TARGET: 1 = re-offended within 2 years
]
df = df[KEEP].copy()

# Remove rows without a valid charge degree
df = df[df["c_charge_degree"].isin(["F", "M"])].reset_index(drop=True)
df = df.dropna(subset=["two_year_recid"]).reset_index(drop=True)

print(f"  After cleaning: {len(df):,} rows")
print(f"  Recidivism rate: {df['two_year_recid'].mean():.1%}")
print(f"  Race breakdown:\n{df['race'].value_counts()}")
print(f"  Sex breakdown:\n{df['sex'].value_counts()}")

# ── 3. Encode categoricals ───────────────────────────────────────────────────
# We keep race and sex as numeric codes so FairLens can split by them,
# but we also save a mapping so results are human-readable.
cat_cols = ["age_cat", "c_charge_degree", "score_text", "race", "sex"]

encoders = {}
df_enc = df.copy()
for col in cat_cols:
    le = LabelEncoder()
    df_enc[col] = le.fit_transform(df_enc[col].astype(str))
    encoders[col] = dict(zip(le.classes_, le.transform(le.classes_)))
    print(f"  Encoded {col}: {encoders[col]}")

# ── 4. Train / test split ────────────────────────────────────────────────────
TARGET = "two_year_recid"
PROTECTED = ["race", "sex"]

X = df_enc.drop(columns=[TARGET])
y = df_enc[TARGET]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# ── 5. Train GradientBoostingClassifier ──────────────────────────────────────
# GBM gives better SHAP values than plain logistic regression for this dataset,
# which makes the FairLens SHAP chart more interesting to look at.
print("\nTraining GradientBoostingClassifier...")
model = GradientBoostingClassifier(
    n_estimators=150,
    learning_rate=0.08,
    max_depth=4,
    subsample=0.8,
    random_state=42,
)
model.fit(X_train, y_train)

y_pred = model.predict(X_test)
acc = accuracy_score(y_test, y_pred)
print(f"  Test accuracy: {acc:.3f}")
print(classification_report(y_test, y_pred, target_names=["No recid.", "Recid."]))

# ── 6. Save model ────────────────────────────────────────────────────────────
with open("compas_model.pkl", "wb") as f:
    pickle.dump(model, f)
print("\nSaved → compas_model.pkl")

# ── 7. Save encoded CSV (this is what you upload to FairLens) ────────────────
# We save the FULL encoded dataset (not just test split) so FairLens has all
# rows for bias analysis across all demographic groups.
df_enc.to_csv("compas_encoded.csv", index=False)
print("Saved → compas_encoded.csv")

# ── 8. Sanity check: predictions.csv preview ─────────────────────────────────
# FairLens model_runner.py will generate this automatically from model.pkl +
# compas_encoded.csv, but this confirms the pipeline works end-to-end.
proba = model.predict_proba(X)[:, 1]
predictions_preview = pd.DataFrame({
    "y_true": y.values,
    "y_pred_proba": np.round(proba, 4),
    "race": df_enc["race"].values,
    "sex": df_enc["sex"].values,
})
predictions_preview.to_csv("compas_predictions_preview.csv", index=False)
print("Saved → compas_predictions_preview.csv  (preview only — FairLens generates the real one)")

print("\n" + "="*55)
print("UPLOAD INSTRUCTIONS FOR FAIRLENS:")
print("  CSV file        : compas_encoded.csv")
print("  Model file      : compas_model.pkl")
print("  Target column   : two_year_recid")
print("  Protected attrs : race, sex")
print("  Positive label  : 1")
print("="*55)
print("\nEncoding reference (for reading FairLens charts):")
for col, mapping in encoders.items():
    print(f"  {col}: {mapping}")
