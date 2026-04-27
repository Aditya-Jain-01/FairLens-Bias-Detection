"""
routers/scenario.py
Handles loading predefined datasets (COMPAS, Law School, Diabetes) directly into the upload flow.
"""

import uuid
import logging
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse

from services import storage
from services.csv_parser import parse_csv
from services.status import set_status
from services.auth import require_api_key
from services.pii_detector import detect_pii
from services.audit_logger import log_event

router = APIRouter()
logger = logging.getLogger("fairlens.scenario")

# Map scenario names to their file prefixes
SCENARIOS = {
    "compas": "compas",
    "lawschool": "lawschool",
    "diabetes": "diabetes"
}

@router.post("/upload/scenario/{scenario_name}", dependencies=[Depends(require_api_key)])
async def load_scenario(scenario_name: str):
    """
    Loads a predefined scenario.
    Returns: { job_id, columns, row_count, pii_scan }
    """
    scenario_name = scenario_name.lower()
    if scenario_name not in SCENARIOS:
        raise HTTPException(status_code=400, detail=f"Invalid scenario. Available: {list(SCENARIOS.keys())}")

    prefix = SCENARIOS[scenario_name]
    
    # Try to find test_data locally (when running from backend dir) or at repo root
    base_dir = Path(__file__).parent.parent
    possible_paths = [
        base_dir / "test_data" / "dummy_data_fairlens",           # If copied inside backend
        base_dir.parent / "test_data" / "dummy_data_fairlens"      # Repo root
    ]
    
    data_dir = None
    for p in possible_paths:
        if p.exists() and p.is_dir():
            data_dir = p
            break
            
    if not data_dir:
        raise HTTPException(status_code=500, detail="Scenario datasets not found on the server.")

    csv_path = data_dir / f"{prefix}_encoded.csv"
    pkl_path = data_dir / f"{prefix}.pkl"

    if not csv_path.exists() or not pkl_path.exists():
        raise HTTPException(status_code=500, detail=f"Missing files for scenario: {prefix}")

    job_id = str(uuid.uuid4())

    try:
        # Parse columns
        try:
            info = parse_csv(csv_path)
        except ValueError as e:
            raise HTTPException(status_code=500, detail=f"Failed to parse scenario CSV: {e}")

        # PII detection
        pii_result = {"has_pii": False, "flagged_columns": []}
        try:
            df_sample = pd.read_csv(csv_path, nrows=5)
            sample_values = {col: df_sample[col].dropna().tolist() for col in df_sample.columns}
            pii_result = detect_pii(info["columns"], sample_values)
        except Exception:
            pass 

        # Persist to storage (both CSV and Model)
        try:
            storage.save_upload_file(job_id, "data.csv", csv_path)
            storage.save_upload_file(job_id, "model.pkl", pkl_path)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Storage error: {e}")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load scenario: {e}")

    # Set initial status
    try:
        set_status(job_id, "uploading", f"Scenario '{scenario_name}' loaded, waiting for configuration.")
    except Exception:
        pass

    # Audit log
    log_event(job_id, "load_scenario", detail={
        "scenario": scenario_name,
        "row_count": info["row_count"],
        "columns": len(info["columns"]),
    })

    return JSONResponse({
        "job_id": job_id,
        "columns": info["columns"],
        "row_count": info["row_count"],
        "pii_scan": pii_result,
        "is_scenario": True
    })
