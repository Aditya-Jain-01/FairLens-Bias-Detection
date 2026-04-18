"""
FairLens — Model trainer for German Credit Risk Dataset
Upload output: model.pkl  +  german_encoded.csv

Dataset source (UCI):
  https://archive.ics.uci.edu/ml/machine-learning-databases/statlog/german/german.data

The raw file has NO header row and uses integer/letter codes for every column.
This script decodes everything, engineers age_group and sex features from the
'personal_status_sex' attribute code, and trains a Random Forest.

Usage:
  pip install pandas scikit-learn
  python train_german_credit.py

Then upload to FairLens:
  - CSV   → german_encoded.csv
  - Model → model.pkl
  - Target column        → credit_risk
  - Protected attributes → age_group, sex
  - Positive outcome     → 1  (good credit = positive)
"""

import pickle
import urllib.request

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

# ── 1. Load raw data (no header, space-separated) ────────────────────────────
URL = "https://archive.ics.uci.edu/ml/machine-learning-databases/statlog/german/german.data"
print("Downloading German Credit dataset...")
urllib.request.urlretrieve(URL, "german_raw.data")

# Official column names from the UCI documentation
COLUMNS = [
    "checking_status",      # A1x: checking account status
    "duration",             # months
    "credit_history",       # A3x
    "purpose",              # A4x: car, furniture, education, etc.
    "credit_amount",        # DM amount
    "savings_status",       # A6x: savings account / bonds
    "employment",           # A7x: years at current job
    "installment_rate",     # % of disposable income
    "personal_status_sex",  # A9x: encodes BOTH sex and marital status
    "other_parties",        # A10x: guarantor / co-applicant
    "residence_since",      # years
    "property_magnitude",   # A12x: real estate, car, etc.
    "age",                  # years
    "other_payment_plans",  # A14x
    "housing",              # A15x: own, free, rent
    "existing_credits",     # number of existing credits
    "job",                  # A17x: skilled, unskilled, etc.
    "num_dependents",       # people liable to provide maintenance for
    "own_telephone",        # A19x
    "foreign_worker",       # A20x
    "credit_risk",          # TARGET: 1 = good, 2 = bad
]

df = pd.read_csv("german_raw.data", sep=" ", header=None, names=COLUMNS)
print(f"  Loaded {len(df):,} rows")

# ── 2. Remap target: UCI uses 1=good, 2=bad → we use 1=good, 0=bad ───────────
df["credit_risk"] = df["credit_risk"].map({1: 1, 2: 0})
print(f"  Good credit rate: {df['credit_risk'].mean():.1%}")

# ── 3. Engineer sex and age_group from encoded columns ───────────────────────
# personal_status_sex codes (from UCI docs):
#   A91 = male: divorced/separated
#   A92 = female: divorced/separated/married
#   A93 = male: single
#   A94 = male: married/widowed
#   A95 = female: single (rare in this dataset)
sex_map = {
    "A91": "male",
    "A92": "female",
    "A93": "male",
    "A94": "male",
    "A95": "female",
}
df["sex"] = df["personal_status_sex"].map(sex_map).fillna("male")

# Age group: under-30 is the most disadvantaged group in this dataset
df["age_group"] = df["age"].apply(lambda x: "under_30" if x < 30 else "30_or_over")

print(f"  Sex breakdown:\n{df['sex'].value_counts()}")
print(f"  Age group breakdown:\n{df['age_group'].value_counts()}")

# ── 4. Encode all categorical columns ────────────────────────────────────────
TARGET = "credit_risk"
DROP = ["personal_status_sex"]          # replaced by engineered 'sex'

df = df.drop(columns=DROP)

cat_cols = df.select_dtypes(include="object").columns.tolist()
encoders = {}
df_enc = df.copy()

for col in cat_cols:
    le = LabelEncoder()
    df_enc[col] = le.fit_transform(df_enc[col].astype(str))
    encoders[col] = dict(zip(le.classes_, map(int, le.transform(le.classes_))))

print("\nEncoded categorical columns:")
for col, mapping in encoders.items():
    print(f"  {col}: {mapping}")

# ── 5. Train / test split ────────────────────────────────────────────────────
X = df_enc.drop(columns=[TARGET])
y = df_enc[TARGET]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# ── 6. Train RandomForestClassifier ──────────────────────────────────────────
# RF gives cleaner SHAP feature importance than logistic regression for this
# dataset because many features are ordinal codes, not truly numeric.
print("\nTraining RandomForestClassifier...")
model = RandomForestClassifier(
    n_estimators=200,
    max_depth=8,
    min_samples_leaf=5,
    class_weight="balanced",    # German Credit has 70/30 class imbalance
    random_state=42,
    n_jobs=-1,
)
model.fit(X_train, y_train)

y_pred = model.predict(X_test)
acc = accuracy_score(y_test, y_pred)
print(f"  Test accuracy: {acc:.3f}")
print(classification_report(y_test, y_pred, target_names=["Bad credit", "Good credit"]))

# ── 7. Save model ────────────────────────────────────────────────────────────
with open("german_credit_model.pkl", "wb") as f:
    pickle.dump(model, f)
print("Saved → german_credit_model.pkl")

# ── 8. Save encoded CSV ──────────────────────────────────────────────────────
df_enc.to_csv("german_encoded.csv", index=False)
print("Saved → german_encoded.csv")

# ── 9. Preview predictions ───────────────────────────────────────────────────
proba = model.predict_proba(X)[:, 1]
pd.DataFrame({
    "y_true": y.values,
    "y_pred_proba": np.round(proba, 4),
    "sex": df_enc["sex"].values,
    "age_group": df_enc["age_group"].values,
}).to_csv("german_credit_predictions_preview.csv", index=False)
print("Saved → german_credit_predictions_preview.csv")

print("\n" + "="*55)
print("UPLOAD INSTRUCTIONS FOR FAIRLENS:")
print("  CSV file        : german_encoded.csv")
print("  Model file      : german_credit_model.pkl")
print("  Target column   : credit_risk")
print("  Protected attrs : sex, age_group")
print("  Positive label  : 1  (good credit)")
print("="*55)
print("\nKey encoding reference:")
print(f"  sex      : {encoders['sex']}")
print(f"  age_group: {encoders['age_group']}")
