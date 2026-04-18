# FairLens Backend — Person 1 Setup Guide

> Everything you need to run, test, and deploy the backend — **no GCP access required** for local development.

---

## Folder Structure

```
fairlens/                          ← project root
│
├── main.py                        ← FastAPI app entry point (Person 1)
├── requirements.txt               ← Python dependencies
├── Dockerfile                     ← Cloud Run container
├── .env                           ← Local environment variables (never commit)
├── .gitignore
├── test_api.py                    ← Smoke-test script (run after server starts)
│
├── routers/
│   ├── __init__.py
│   ├── upload.py                  ← POST /upload/csv  POST /upload/model  (Person 1 ✅)
│   ├── analyze.py                 ← POST /analyze/configure  GET /status/{id}  (Person 1 ✅)
│   ├── remediate.py               ← stub → Person 2 fills in
│   ├── explain.py                 ← stub → Person 3 fills in
│   └── report.py                  ← stub → Person 3 fills in
│
├── services/
│   ├── __init__.py
│   ├── storage.py                 ← GCS ↔ local disk abstraction (Person 1 ✅)
│   ├── status.py                  ← read/write status.json (Person 1 ✅)
│   ├── csv_parser.py              ← parse uploaded CSV (Person 1 ✅)
│   └── inference.py               ← run .pkl / .onnx model (Person 1 ✅)
│
├── mocks/
│   ├── __init__.py
│   └── mock_data.py               ← MOCK_RESULTS + MOCK_EXPLANATION (matches CONTRACT.md)
│
└── storage_local/                 ← created automatically at runtime
    ├── uploads/{job_id}/          ← data.csv, model.pkl, predictions.csv, config.json, status.json
    └── results/{job_id}/          ← results.json, explanation.json, report.pdf
```

---

## Quick Start (Local — No GCP Needed)

### Step 1 — Clone & create virtual environment

```bash
git clone <repo-url>
cd fairlens

python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
```

### Step 2 — Install dependencies

```bash
pip install -r requirements.txt
```

### Step 3 — Configure environment

The `.env` file is already set up for local development. Key settings:

```ini
USE_LOCAL_STORAGE=true        # ← uses ./storage_local/ instead of GCS
USE_MOCK_PIPELINE=true        # ← auto-fills results + explanation after upload
```

Leave these as `true` until you have GCP credentials.

### Step 4 — Start the server

```bash
uvicorn main:app --reload --port 8000
```

You should see:
```
✅ Storage mode: LOCAL DISK (no GCP needed)
✅ Ready — visit http://localhost:8000/docs
```

### Step 5 — Open the API docs

Visit: **http://localhost:8000/docs**

This is the interactive Swagger UI — you can test every endpoint right in the browser.

### Step 6 — Run the smoke tests (in a second terminal)

```bash
python3 test_api.py
```

Expected output:
```
══════════════════════════════════════════
  FairLens API Smoke Tests
  Target: http://localhost:8000
══════════════════════════════════════════

── Infra ──
  ✅ GET /health — ok
  ✅ GET /

── Upload ──
  ✅ POST /upload/csv — job_id=3f7a1b2c...
  ✅ CSV returns columns — ['age', 'gender', 'race']
  ✅ CSV returns row_count — 10
  ✅ POST /upload/model — model_type=sklearn

── Analyze ──
  ✅ POST /analyze/configure — queued

── Status ──
  ✅ GET /status/{job_id} — stage=uploading
  ✅ Status has progress — 5
  ✅ GET /status/{bad_id} returns error stage

── Demo ──
  ✅ POST /analyze/configure (demo) 
  ✅ GET /status/demo — stage=uploading

── Stubs (Person 2 & 3) ──
  ✅ GET /remediate/threshold (stub)
  ✅ GET /report/{job_id} (stub)

══════════════════════════════════════════
  13/13 tests passed
  🎉 All good! Server is working correctly.
══════════════════════════════════════════
```

---

## Full End-to-End Demo Flow

This tests the complete frontend → backend loop using mock data:

### 1. Tell server to use mock pipeline

In `.env`, set:
```ini
USE_MOCK_PIPELINE=true
```
Restart the server.

### 2. Upload a CSV

```bash
curl -X POST http://localhost:8000/api/v1/upload/csv \
  -F "file=@your_data.csv"
```

Response:
```json
{ "job_id": "abc123", "columns": ["age", "gender", ...], "row_count": 1000 }
```

### 3. Configure the job

```bash
curl -X POST http://localhost:8000/api/v1/analyze/configure \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "abc123",
    "target_column": "income",
    "protected_attributes": ["gender", "race"],
    "positive_outcome_label": 1
  }'
```

### 4. Poll status

```bash
watch -n 2 curl -s http://localhost:8000/api/v1/status/abc123
```

With `USE_MOCK_PIPELINE=true`, the status moves through all stages automatically and ends at `"complete"` in about 6 seconds.

### 5. Try the demo button (pre-seeded)

```bash
curl -X POST http://localhost:8000/api/v1/analyze/configure \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "demo",
    "target_column": "income",
    "protected_attributes": ["gender", "race"],
    "positive_outcome_label": 1
  }'
```

Then poll `/status/demo` — results and explanation are immediately seeded from mock data.

---

## Environment Variables Reference

| Variable | Default | Description |
|---|---|---|
| `USE_LOCAL_STORAGE` | `true` | Use local disk instead of GCS |
| `LOCAL_UPLOAD_DIR` | `./storage_local/uploads` | Local upload directory |
| `LOCAL_RESULTS_DIR` | `./storage_local/results` | Local results directory |
| `USE_MOCK_PIPELINE` | `false` | Auto-inject mock results after upload |
| `GCP_PROJECT_ID` | — | GCP project (needed when USE_LOCAL_STORAGE=false) |
| `GCS_UPLOAD_BUCKET` | `fairlens-uploads` | GCS bucket for uploads |
| `GCS_RESULTS_BUCKET` | `fairlens-results` | GCS bucket for results |
| `FRONTEND_URL` | `http://localhost:3000` | Allowed CORS origin |

---

## Switching to GCP (When You Get Access)

### Step 1 — Install GCP deps

```bash
pip install google-cloud-storage==2.17.0
```

### Step 2 — Authenticate

```bash
gcloud auth application-default login
gcloud config set project fairlens-hackathon
```

### Step 3 — Create GCS buckets

```bash
gsutil mb -l us-central1 gs://fairlens-uploads
gsutil mb -l us-central1 gs://fairlens-results
```

### Step 4 — Update `.env`

```ini
USE_LOCAL_STORAGE=false
GCP_PROJECT_ID=fairlens-hackathon
GCS_UPLOAD_BUCKET=fairlens-uploads
GCS_RESULTS_BUCKET=fairlens-results
```

Restart server — everything else is identical.

### Step 5 — Deploy to Cloud Run

```bash
# Build and push container
gcloud builds submit --tag gcr.io/fairlens-hackathon/fairlens-api

# Deploy
gcloud run deploy fairlens-api \
  --image gcr.io/fairlens-hackathon/fairlens-api \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars USE_LOCAL_STORAGE=false,GCP_PROJECT_ID=fairlens-hackathon,GCS_UPLOAD_BUCKET=fairlens-uploads,GCS_RESULTS_BUCKET=fairlens-results
```

Copy the deployed URL and share it with the team as `NEXT_PUBLIC_API_URL`.

---

## API Routes — Person 1 Owns

| Method | Route | Status |
|---|---|---|
| POST | `/api/v1/upload/csv` | ✅ Complete |
| POST | `/api/v1/upload/model` | ✅ Complete |
| POST | `/api/v1/analyze/configure` | ✅ Complete |
| GET  | `/api/v1/status/{job_id}` | ✅ Complete |
| GET  | `/health` | ✅ Complete |
| GET  | `/` | ✅ Complete |

## API Routes — Stubs (Other Persons Fill In)

| Method | Route | Owner |
|---|---|---|
| GET  | `/api/v1/results/{job_id}` | Person 2 |
| POST | `/api/v1/remediate/reweigh` | Person 2 |
| GET  | `/api/v1/remediate/threshold` | Person 2 |
| POST | `/api/v1/explain` | Person 3 |
| POST | `/api/v1/ask` | Person 3 |
| GET  | `/api/v1/report/{job_id}` | Person 3 |

---

## Integration Day Checklist

- [ ] Person 2 replaces body of `routers/remediate.py`
- [ ] Person 3 replaces body of `routers/explain.py` and `routers/report.py`
- [ ] Set `USE_LOCAL_STORAGE=false` once GCP is ready
- [ ] Set `USE_MOCK_PIPELINE=false`
- [ ] Share Cloud Run URL with Person 4 as `NEXT_PUBLIC_API_URL`
- [ ] Test with `python3 test_api.py https://your-cloudrun-url.run.app`

---

## Notes for Teammates

**Person 2** — Your worker should:
1. Poll `storage.read_json(job_id, "status.json", bucket="uploads")` until `stage == "computing_metrics"`
2. Read `storage.get_local_file_path(job_id, "data.csv")` and `predictions.csv`
3. Write results to `storage.write_json(job_id, "results.json", data, bucket="results")`
4. Call `set_status(job_id, "generating_explanation", "...")` when done

**Person 3** — Your worker should:
1. Poll until `stage == "generating_explanation"`
2. Read `storage.read_json(job_id, "results.json", bucket="results")`
3. Call Gemini, write `storage.write_json(job_id, "explanation.json", data, bucket="results")`
4. Generate PDF, then `set_status(job_id, "complete", "Audit complete!")`

Both of you import from `services.storage` and `services.status` — no need to touch `main.py`.
