# FairLens

AI-powered bias detection and remediation platform for ML models.

## Project Structure

```
fairlens/
├── backend/          # FastAPI backend — deployable on Google Cloud Run
├── frontend/         # Next.js frontend
├── test_data/        # Sample datasets and model training scripts
└── docs/             # API contract and reference artifacts
    ├── CONTRACT.md
    └── artifacts/    # Sample results and test outputs from development
```

## Running Locally

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
# API available at http://localhost:8000
# Docs at http://localhost:8000/docs
```

### Frontend
```bash
cd frontend
npm install
npm run dev
# Open http://localhost:3000
```

Create `frontend/.env.local`:
```
NEXT_PUBLIC_USE_MOCK=false
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

Or point it at the deployed backend:
```
NEXT_PUBLIC_USE_MOCK=false
NEXT_PUBLIC_API_URL=<your-cloud-run-url>/api/v1
```

## Deploying to Google Cloud Run

```bash
cd backend
gcloud builds submit --tag us-central1-docker.pkg.dev/<your-project-id>/fairlens/fairlens-api .

gcloud run deploy fairlens-api \
  --image us-central1-docker.pkg.dev/<your-project-id>/fairlens/fairlens-api \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "USE_LOCAL_STORAGE=false,GCP_PROJECT_ID=<your-project-id>,GCS_UPLOAD_BUCKET=<your-upload-bucket>,GCS_RESULTS_BUCKET=<your-results-bucket>,VERTEX_AI_LOCATION=us-central1,GEMINI_MODEL=gemini-1.5-pro"
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `USE_LOCAL_STORAGE` | `true` for local disk, `false` for GCS |
| `USE_MOCK_PIPELINE` | `true` to skip real bias analysis |
| `GCP_PROJECT_ID` | Your GCP project ID |
| `GCS_UPLOAD_BUCKET` | GCS bucket for uploaded files |
| `GCS_RESULTS_BUCKET` | GCS bucket for analysis results |
| `VERTEX_AI_LOCATION` | e.g. `us-central1` |
| `GEMINI_MODEL` | e.g. `gemini-1.5-pro` |

## API Reference

Full API docs available at `/docs` when the backend is running.  
See `docs/CONTRACT.md` for the complete data contract.
