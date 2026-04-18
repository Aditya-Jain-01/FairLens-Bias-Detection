# FairLens — Team Contract

> **READ THIS BEFORE WRITING ANY CODE.**
> This file defines every shared interface between the 4 workstreams.
> Nobody changes anything here without a group decision. This is the single source of truth.

---

## 1. GCS Folder Structure

Every job has a `job_id` (UUID4 string). All files live under:

```
fairlens-uploads/{job_id}/
    data.csv              # uploaded dataset (Person 1 writes)
    model.pkl             # uploaded model file, if any (Person 1 writes)
    predictions.csv       # model output predictions (Person 1 writes)
    config.json           # analysis configuration (Person 1 writes)

fairlens-results/{job_id}/
    results.json          # bias metrics + SHAP + remediation (Person 2 writes)
    explanation.json      # Gemini structured output (Person 3 writes)
    report.pdf            # generated audit PDF (Person 3 writes)
    status.json           # job progress (Person 1 writes, all read)
```

---

## 2. config.json Schema

Written by Person 1 after the user configures their upload.

```json
{
  "job_id": "3f7a1b2c-...",
  "dataset_path": "fairlens-uploads/3f7a1b2c/data.csv",
  "model_path": "fairlens-uploads/3f7a1b2c/model.pkl",
  "predictions_path": "fairlens-uploads/3f7a1b2c/predictions.csv",
  "target_column": "loan_approved",
  "protected_attributes": ["gender", "race"],
  "positive_outcome_label": 1,
  "created_at": "2025-01-01T10:00:00Z"
}
```

---

## 3. status.json Schema

Written by Person 1, polled by Person 4 frontend every 2 seconds.

```json
{
  "job_id": "3f7a1b2c-...",
  "stage": "computing_metrics",
  "progress": 45,
  "message": "Running fairness metrics...",
  "error": null
}
```

**Valid `stage` values (in order):**
- `"uploading"` — file upload in progress
- `"configuring"` — waiting for user to set protected attributes
- `"running_inference"` — model predictions being generated
- `"computing_metrics"` — Person 2's bias engine running
- `"generating_explanation"` — Person 3's Gemini call in progress
- `"generating_report"` — PDF being rendered
- `"complete"` — all done, dashboard ready
- `"error"` — something failed, check `error` field

---

## 4. results.json Schema

**The most important contract.** Written by Person 2. Read by Person 3 (Gemini) and Person 4 (dashboard).

```json
{
  "job_id": "3f7a1b2c-...",
  "completed_at": "2025-01-01T10:05:00Z",
  "dataset_info": {
    "total_rows": 48842,
    "target_column": "loan_approved",
    "protected_attributes": ["gender", "race"],
    "positive_rate_overall": 0.241
  },
  "metrics": {
    "disparate_impact": {
      "value": 0.62,
      "threshold": 0.8,
      "passed": false,
      "description": "Ratio of positive outcome rate between unprivileged and privileged group. Must be >= 0.8 (80% rule)."
    },
    "demographic_parity_difference": {
      "value": -0.193,
      "threshold": 0.1,
      "passed": false,
      "description": "Difference in positive prediction rates between groups. Should be close to 0."
    },
    "equalized_odds_difference": {
      "value": -0.142,
      "threshold": 0.1,
      "passed": false,
      "description": "Difference in TPR between groups. Should be close to 0."
    },
    "calibration_difference": {
      "value": 0.031,
      "threshold": 0.1,
      "passed": true,
      "description": "Difference in score reliability across groups."
    }
  },
  "per_group_stats": {
    "gender": {
      "Male":   { "count": 21790, "positive_rate": 0.308, "tpr": 0.742, "fpr": 0.181 },
      "Female": { "count": 10771, "positive_rate": 0.115, "tpr": 0.600, "fpr": 0.062 }
    },
    "race": {
      "White":            { "count": 27816, "positive_rate": 0.261, "tpr": 0.731, "fpr": 0.162 },
      "Black":            { "count": 3124,  "positive_rate": 0.122, "tpr": 0.589, "fpr": 0.091 },
      "Asian-Pac-Islander": { "count": 1039, "positive_rate": 0.276, "tpr": 0.701, "fpr": 0.130 },
      "Other":            { "count": 271,   "positive_rate": 0.143, "tpr": 0.612, "fpr": 0.105 }
    }
  },
  "overall_severity": "high",
  "metrics_passed": 1,
  "metrics_failed": 3,
  "shap": {
    "top_features": [
      { "feature": "capital_gain",      "importance": 0.312, "direction": "positive" },
      { "feature": "age",               "importance": 0.198, "direction": "positive" },
      { "feature": "education_num",     "importance": 0.167, "direction": "positive" },
      { "feature": "hours_per_week",    "importance": 0.143, "direction": "positive" },
      { "feature": "marital_status",    "importance": 0.089, "direction": "negative" },
      { "feature": "occupation",        "importance": 0.051, "direction": "mixed"    },
      { "feature": "relationship",      "importance": 0.040, "direction": "negative" }
    ],
    "protected_attr_shap": {
      "gender": 0.028,
      "race":   0.019
    },
    "note": "Higher protected_attr_shap means the protected attribute is directly influencing predictions."
  },
  "remediation": {
    "reweighing": {
      "applied": true,
      "metrics_after": {
        "disparate_impact":              { "value": 0.84, "passed": true  },
        "demographic_parity_difference": { "value": -0.048, "passed": true  },
        "equalized_odds_difference":     { "value": -0.071, "passed": true  },
        "calibration_difference":        { "value": 0.038, "passed": true  }
      },
      "accuracy_before": 0.847,
      "accuracy_after":  0.831,
      "accuracy_delta":  -0.016
    },
    "threshold": {
      "current_threshold": 0.5,
      "privileged_group":   "Male",
      "unprivileged_group": "Female"
    }
  }
}
```

**Severity rules (Person 2 must implement):**
- `"high"` — 2 or more metrics failed
- `"medium"` — exactly 1 metric failed
- `"low"` — all metrics passed but values are close to thresholds
- `"none"` — all metrics passed comfortably

---

## 5. explanation.json Schema

Written by Person 3 (Gemini output). Read by Person 4 (dashboard panel).

```json
{
  "job_id": "3f7a1b2c-...",
  "generated_at": "2025-01-01T10:06:00Z",
  "summary": "Your model shows significant gender and racial bias. Women are approved at 37% the rate of men despite similar financial profiles.",
  "severity_label": "High bias detected",
  "findings": [
    {
      "id": "f1",
      "attribute": "gender",
      "metric": "disparate_impact",
      "headline": "Women approved 38% less often than men",
      "detail": "The disparate impact ratio of 0.62 falls well below the legal 80% threshold. This means female applicants receive positive outcomes at 62% the rate of male applicants.",
      "severity": "high"
    },
    {
      "id": "f2",
      "attribute": "race",
      "metric": "equalized_odds_difference",
      "headline": "Black applicants face lower true positive rates",
      "detail": "Even when Black applicants qualify, the model correctly identifies them 14.2 percentage points less often than White applicants.",
      "severity": "high"
    }
  ],
  "recommended_fix": "reweighing",
  "recommended_fix_reason": "Reweighing reduces disparate impact to 0.84 (above the 0.8 legal threshold) with only a 1.6% accuracy trade-off — the best balance for this dataset.",
  "plain_english": "If you deployed this model today, it would systematically disadvantage women and Black applicants in ways that could violate equal credit opportunity laws. The good news: applying reweighing correction brings the model into compliance while keeping accuracy above 83%."
}
```

---

## 6. API Routes Contract

All routes are prefixed with `/api/v1`. Base URL from Person 1's Cloud Run deployment.

| Method | Route | Owner | Input | Output |
|--------|-------|-------|-------|--------|
| POST | `/upload/csv` | P1 | multipart CSV file | `{job_id, columns[], row_count}` |
| POST | `/upload/model` | P1 | multipart model file + job_id | `{job_id, model_type}` |
| POST | `/analyze/configure` | P1 | `{job_id, target_column, protected_attributes[], positive_outcome_label}` | `{job_id, status: "queued"}` |
| GET | `/status/{job_id}` | P1 | — | status.json contents |
| GET | `/results/{job_id}` | P2 | — | results.json contents |
| POST | `/remediate/reweigh` | P2 | `{job_id}` | updated results with reweighing applied |
| GET | `/remediate/threshold` | P2 | `?job_id=x&threshold=0.6` | `{metrics_at_threshold, accuracy}` |
| POST | `/explain` | P3 | `{job_id}` | SSE stream of text chunks |
| POST | `/ask` | P3 | `{job_id, question}` | `{answer}` |
| GET | `/report/{job_id}` | P3 | — | `{download_url}` |

---

## 7. Environment Variables

All stored in GCP Secret Manager. Person 1 sets these up and shares the `.env.local` file privately (never commit to git).

```
GCP_PROJECT_ID=fairlens-hackathon
GCP_REGION=us-central1
GCS_UPLOAD_BUCKET=fairlens-uploads
GCS_RESULTS_BUCKET=fairlens-results
VERTEX_AI_LOCATION=us-central1
GEMINI_MODEL=gemini-1.5-pro
FIREBASE_PROJECT_ID=fairlens-hackathon
FRONTEND_URL=https://fairlens.vercel.app
BACKEND_URL=https://fairlens-api-xxxx-uc.a.run.app
```

---

## 8. Mock Data

Person 4 builds the frontend against this mock before the real API is ready.
File: `frontend/mocks/results.json` — copy the results.json example from section 4 above.
File: `frontend/mocks/explanation.json` — copy the explanation.json example from section 5 above.

The frontend API client should check `process.env.NEXT_PUBLIC_USE_MOCK === "true"` and return mock data instead of calling the real API. Flip the env var on integration day.

---

## 9. Demo Dataset

Use the **Adult Income dataset** (UCI) — available at:
`https://archive.ics.uci.edu/ml/machine-learning-databases/adult/adult.data`

- Target column: `income` (>50K = 1, <=50K = 0)
- Protected attributes: `sex`, `race`
- 48,842 rows — enough to show real bias statistics
- Pre-trained sklearn LogisticRegression model: Person 2 trains and saves as `demo_model.pkl`
- Person 1 pre-loads this into GCS as `fairlens-uploads/demo/` so Person 4 can wire a "Try demo" button

---

*Last updated: day 0. All changes require group agreement.*
