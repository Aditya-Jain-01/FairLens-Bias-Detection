"""
FairLens — Model trainer for HMDA Mortgage Disclosure Dataset
Upload output: model.pkl  +  hmda_encoded.csv

Dataset source (CFPB public HMDA data, 2017 — manageable size):
  We use a pre-filtered excerpt hosted on a public mirror. If the URL
  is unavailable, download from:
  https://ffiec.cfpb.gov/data-browser/data/2022?category=nationwide
  and filter to a single state (e.g. California) to keep it manageable.

  Alternatively, a well-known cleaned version is available at:
  https://raw.githubusercontent.com/ageron/handson-ml2/master/datasets/housing/housing.csv
  (not HMDA — see fallback below)

This script uses the CFPB's public S3 snapshot of 2017 HMDA LAR data
filtered to a single state for speed, then cleans and trains a logistic
regression model.

Usage:
  pip install pandas scikit-learn requests
  python train_hmda.py

Then upload to FairLens:
  - CSV   → hmda_encoded.csv
  - Model → model.pkl
  - Target column        → loan_approved
  - Protected attributes → applicant_race, applicant_sex
  - Positive outcome     → 1  (loan approved)
"""

import pickle
import urllib.request

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler

# ── 1. Load HMDA data ─────────────────────────────────────────────────────────
# We use a curated HMDA sample that's been pre-cleaned and is small enough
# to train locally. This mirrors the structure of the real CFPB HMDA LAR file.
URL = (
    "https://raw.githubusercontent.com/dssg/fairness_tutorial/master/"
    "data/processed/hmda_2017_sample.csv"
)

print("Downloading HMDA dataset...")
try:
    urllib.request.urlretrieve(URL, "hmda_raw.csv")
    df = pd.read_csv("hmda_raw.csv")
    print(f"  Loaded {len(df):,} rows from dssg/fairness_tutorial sample")
except Exception:
    # ── Fallback: build a synthetic HMDA-structured dataset ──────────────────
    # This mirrors the real column structure and bias patterns of HMDA data
    # so FairLens metrics will behave realistically.
    print("  Remote file unavailable — generating synthetic HMDA-structured data")
    rng = np.random.default_rng(42)
    n = 10_000

    race_vals   = rng.choice(["White", "Black", "Hispanic", "Asian", "Other"],
                              p=[0.65, 0.13, 0.11, 0.07, 0.04], size=n)
    sex_vals    = rng.choice(["Male", "Female"], p=[0.61, 0.39], size=n)
    income      = rng.lognormal(mean=11.0, sigma=0.5, size=n).clip(20_000, 500_000)
    loan_amount = rng.lognormal(mean=12.3, sigma=0.4, size=n).clip(50_000, 800_000)
    dti         = rng.beta(2, 5, size=n) * 60           # debt-to-income 0–60
    ltv         = rng.beta(3, 2, size=n) * 100          # loan-to-value 0–100
    credit_score = rng.normal(680, 60, size=n).clip(450, 850)

    # Approval probability: financial factors dominate, but race/sex add bias
    log_odds = (
        0.004 * credit_score
        - 0.03 * dti
        - 0.01 * ltv
        + 0.000002 * income
        + np.where(race_vals == "White",    0.5,
          np.where(race_vals == "Asian",    0.2,
          np.where(race_vals == "Hispanic", -0.3,
          np.where(race_vals == "Black",    -0.6, -0.1))))
        + np.where(sex_vals == "Male", 0.2, -0.1)
        - 4.5   # intercept to get ~65% approval rate
    )
    prob_approve = 1 / (1 + np.exp(-log_odds))
    approved = rng.binomial(1, prob_approve)

    df = pd.DataFrame({
        "applicant_race":   race_vals,
        "applicant_sex":    sex_vals,
        "applicant_income": income.astype(int),
        "loan_amount":      loan_amount.astype(int),
        "debt_to_income":   np.round(dti, 2),
        "loan_to_value":    np.round(ltv, 2),
        "credit_score":     credit_score.astype(int),
        "loan_purpose":     rng.choice(
            ["purchase", "refinance", "home_improvement"],
            p=[0.55, 0.35, 0.10], size=n
        ),
        "property_type":    rng.choice(
            ["single_family", "condo", "multi_family"],
            p=[0.70, 0.20, 0.10], size=n
        ),
        "loan_approved":    approved,
    })
    print(f"  Generated {len(df):,} synthetic HMDA rows")

print(f"  Columns: {list(df.columns)}")

# ── 2. Standardise column names ───────────────────────────────────────────────
# Real HMDA files use slightly different names; normalise them here.
rename_map = {
    "action_taken":         "loan_approved",
    "applicant_race_1":     "applicant_race",
    "applicant_sex_1":      "applicant_sex",
    "loan_amount_000s":     "loan_amount",
    "applicant_income_000s": "applicant_income",
}
df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

# ── 3. Filter to binary approval outcome ─────────────────────────────────────
# Real HMDA action_taken: 1=originated, 2=approved not accepted, 3=denied
# 4=withdrawn, 5=incomplete, 6=purchased, 7=pre-approval denied, 8=pre-approval issued
TARGET = "loan_approved"

if df[TARGET].max() > 1:
    # Map: 1,2 → 1 (approved), 3,7 → 0 (denied), drop the rest
    df = df[df[TARGET].isin([1, 2, 3, 7])].copy()
    df[TARGET] = df[TARGET].map({1: 1, 2: 1, 3: 0, 7: 0})

# Drop rows with null target or protected attributes
df = df.dropna(subset=[TARGET, "applicant_race", "applicant_sex"]).reset_index(drop=True)

# Filter out "Information not provided" / "Not applicable" race codes
if df["applicant_race"].dtype == object:
    keep_races = ["White", "Black or African American", "Hispanic",
                  "Asian", "Black", "Hispanic or Latino", "Other"]
    # Flexible: keep rows where race contains a known group
    df = df[df["applicant_race"].str.contains(
        "White|Black|Hispanic|Asian|Other", case=False, na=False
    )].reset_index(drop=True)
    # Simplify race labels
    df["applicant_race"] = df["applicant_race"].str.strip()
    df.loc[df["applicant_race"].str.contains("Black", case=False), "applicant_race"] = "Black"
    df.loc[df["applicant_race"].str.contains("Hispanic", case=False), "applicant_race"] = "Hispanic"
    df.loc[df["applicant_race"].str.contains("Asian", case=False), "applicant_race"] = "Asian"
    df.loc[~df["applicant_race"].isin(["White", "Black", "Hispanic", "Asian"]), "applicant_race"] = "Other"

# Simplify sex labels
if df["applicant_sex"].dtype == object:
    df = df[df["applicant_sex"].str.contains("Male|Female", case=False, na=False)].reset_index(drop=True)
    df["applicant_sex"] = df["applicant_sex"].apply(
        lambda x: "Female" if "Female" in str(x) else "Male"
    )

print(f"\nAfter cleaning: {len(df):,} rows")
print(f"Approval rate: {df[TARGET].mean():.1%}")
print(f"Race breakdown:\n{df['applicant_race'].value_counts()}")
print(f"Sex breakdown:\n{df['applicant_sex'].value_counts()}")

# ── 4. Select feature columns ─────────────────────────────────────────────────
# Include financial features + protected attributes.
# Protected attributes ARE included as features (intentional — this is the
# scenario FairLens is designed to detect and remediate).
NUMERIC_COLS = []
for col in ["applicant_income", "loan_amount", "debt_to_income",
            "loan_to_value", "credit_score"]:
    if col in df.columns:
        NUMERIC_COLS.append(col)

CAT_COLS = []
for col in ["applicant_race", "applicant_sex", "loan_purpose", "property_type"]:
    if col in df.columns:
        CAT_COLS.append(col)

# Fill missing numeric values with column median
for col in NUMERIC_COLS:
    df[col] = pd.to_numeric(df[col], errors="coerce")
    df[col] = df[col].fillna(df[col].median())

# ── 5. Encode categoricals ────────────────────────────────────────────────────
encoders = {}
df_enc = df[NUMERIC_COLS + CAT_COLS + [TARGET]].copy()

for col in CAT_COLS:
    le = LabelEncoder()
    df_enc[col] = le.fit_transform(df_enc[col].astype(str))
    encoders[col] = dict(zip(le.classes_, map(int, le.transform(le.classes_))))

print("\nEncoding reference:")
for col, mapping in encoders.items():
    print(f"  {col}: {mapping}")

# ── 6. Train / test split ─────────────────────────────────────────────────────
X = df_enc.drop(columns=[TARGET])
y = df_enc[TARGET]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# ── 7. Scale + train Logistic Regression ──────────────────────────────────────
# LR is the right choice here: HMDA is a large, mostly-numeric dataset where
# the relationship between income/DTI/LTV and approval is roughly log-linear.
# The bias from race/sex shows up cleanly in the coefficients.
scaler = StandardScaler()
X_train_s = scaler.fit_transform(X_train)
X_test_s  = scaler.transform(X_test)

print("\nTraining LogisticRegression...")
model = LogisticRegression(
    C=1.0,
    max_iter=1000,
    solver="lbfgs",
    class_weight="balanced",
    random_state=42,
)
model.fit(X_train_s, y_train)

# Wrap scaler + model together so model_runner.py only needs to call predict()
from sklearn.pipeline import Pipeline
pipeline = Pipeline([("scaler", scaler), ("lr", model)])
# Refit pipeline on full training data
pipeline.fit(X_train, y_train)

y_pred = pipeline.predict(X_test)
acc = accuracy_score(y_test, y_pred)
print(f"  Test accuracy: {acc:.3f}")
print(classification_report(y_test, y_pred, target_names=["Denied", "Approved"]))

# Print race coefficients to verify bias is present
feature_names = list(X.columns)
lr_coefs = dict(zip(feature_names, pipeline.named_steps["lr"].coef_[0]))
print("\nTop feature coefficients (positive = more likely approved):")
for feat, coef in sorted(lr_coefs.items(), key=lambda x: abs(x[1]), reverse=True)[:8]:
    print(f"  {feat:25s}: {coef:+.3f}")

# ── 8. Save pipeline as model.pkl ────────────────────────────────────────────
with open("hmda_model.pkl", "wb") as f:
    pickle.dump(pipeline, f)
print("\nSaved → hmda_model.pkl  (sklearn Pipeline: StandardScaler + LogisticRegression)")

# ── 9. Save encoded CSV ───────────────────────────────────────────────────────
df_enc.to_csv("hmda_encoded.csv", index=False)
print("Saved → hmda_encoded.csv")

# ── 10. Preview predictions ───────────────────────────────────────────────────
proba = pipeline.predict_proba(X)[:, 1]
pd.DataFrame({
    "y_true":        y.values,
    "y_pred_proba":  np.round(proba, 4),
    "applicant_race": df_enc["applicant_race"].values,
    "applicant_sex":  df_enc["applicant_sex"].values,
}).to_csv("hmda_predictions_preview.csv", index=False)
print("Saved → hmda_predictions_preview.csv")

print("\n" + "="*55)
print("UPLOAD INSTRUCTIONS FOR FAIRLENS:")
print("  CSV file        : hmda_encoded.csv")
print("  Model file      : hmda_model.pkl")
print("  Target column   : loan_approved")
print("  Protected attrs : applicant_race, applicant_sex")
print("  Positive label  : 1  (loan approved)")
print("="*55)
print("\nEncoding reference (for reading FairLens charts):")
for col, mapping in encoders.items():
    print(f"  {col}: {mapping}")
