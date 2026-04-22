import pandas as pd
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

MAX_ROWS = 2_000_000
MIN_ROWS = 50
MAX_COLUMNS = 500

def validate_csv(path: str, config: dict) -> dict:
    """
    Validates uploaded CSV before analysis begins.
    Returns cleaned metadata or raises HTTPException with a user-friendly message.
    """
    try:
        df = pd.read_csv(path, nrows=MAX_ROWS + 1)
    except Exception as e:
        raise HTTPException(400, f"Cannot parse CSV: {e}")

    if len(df) < MIN_ROWS:
        raise HTTPException(400, f"Dataset too small: {len(df)} rows. Minimum is {MIN_ROWS}.")

    if len(df) > MAX_ROWS:
        raise HTTPException(400, f"Dataset too large: {len(df)} rows. Maximum is {MAX_ROWS:,}.")

    if len(df.columns) > MAX_COLUMNS:
        raise HTTPException(400, f"Too many columns: {len(df.columns)}. Maximum is {MAX_COLUMNS}.")

    target = config.get("target_column")
    if target and target not in df.columns:
        raise HTTPException(400, f"Target column '{target}' not found in CSV.")

    if target:
        unique_vals = df[target].nunique()
        if unique_vals > 20:
            raise HTTPException(400,
                f"Target column '{target}' has {unique_vals} unique values. "
                f"FairLens supports binary or low-cardinality classification targets only."
            )

    protected = config.get("protected_attributes", [])
    for attr in protected:
        if attr not in df.columns:
            raise HTTPException(400, f"Protected attribute '{attr}' not found in CSV columns.")
        if df[attr].nunique() > 50:
            raise HTTPException(400,
                f"Protected attribute '{attr}' has too many unique values ({df[attr].nunique()}). "
                f"This attribute may be continuous — please encode it into groups first."
            )

    missing_pct = df.isnull().mean().mean()
    if missing_pct > 0.4:
        raise HTTPException(400,
            f"Dataset has {missing_pct:.0%} missing values. "
            f"Please clean the data before uploading."
        )

    return {
        "rows": len(df),
        "columns": list(df.columns),
        "missing_pct": round(missing_pct, 4) if pd.notna(missing_pct) else 0.0,
        "target_unique_values": int(df[target].nunique()) if target else None,
    }
