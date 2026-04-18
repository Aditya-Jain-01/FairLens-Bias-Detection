# ── FairLens API — Cloud Run Container ──
# Build: gcloud builds submit --tag gcr.io/$PROJECT_ID/fairlens-api .
# Deploy: gcloud run deploy fairlens-api --image gcr.io/$PROJECT_ID/fairlens-api ...

FROM python:3.12-slim

# Set working directory
WORKDIR /app

# System deps:
#   gcc       — required for pandas/numpy/shap wheel builds
#   libpango / libcairo / libgdk-pixbuf — required by WeasyPrint (PDF rendering)
#   shared-mime-info / libffi — required by WeasyPrint
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    libgdk-pixbuf-xlib-2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (Docker cache layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Cloud Run injects the PORT env var (default 8080)
# USE_LOCAL_STORAGE=false → all I/O goes to GCS, not local disk
# USE_MOCK_PIPELINE=false → run the real bias engine, not mock data
ENV PORT=8080
ENV USE_LOCAL_STORAGE=false
ENV USE_MOCK_PIPELINE=false

# Run with uvicorn — Cloud Run sends SIGTERM for graceful shutdown
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]

EXPOSE 8080
