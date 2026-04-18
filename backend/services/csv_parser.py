"""
services/csv_parser.py
Validates and parses uploaded CSV files.

Returns column names, row count, and detected dtypes so the frontend
can show users what columns are available for analysis configuration.
"""

from pathlib import Path
import csv

MAX_PREVIEW_ROWS = 5

def parse_csv(file_path: Path) -> dict:
    """
    Parse a CSV file and return schema information using pure Python.
    """
    if str(file_path).startswith("file://"):
        file_path = Path(str(file_path).replace("file://", ""))
        
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            try:
                headers = next(reader)
            except StopIteration:
                raise ValueError("CSV file is empty.")
            if not headers:
                raise ValueError("CSV file has no columns.")
            rows = []
            row_count = 0
            for row in reader:
                if row:
                    row_count += 1
                    if len(rows) < MAX_PREVIEW_ROWS:
                        rows.append(row)
    except UnicodeDecodeError:
        # Fallback: try latin-1 (common for Excel-exported CSVs on Windows)
        with open(file_path, "r", encoding="latin-1") as f:
            reader = csv.reader(f)
            try:
                headers = next(reader)
            except StopIteration:
                raise ValueError("CSV file is empty.")
            if not headers:
                raise ValueError("CSV file has no columns.")
            rows = []
            row_count = 0
            for row in reader:
                if row:
                    row_count += 1
                    if len(rows) < MAX_PREVIEW_ROWS:
                        rows.append(row)

                
    except Exception as e:
        if isinstance(e, ValueError):
            raise
        raise ValueError(f"Could not read CSV: {e}")

    columns = [str(h).strip() for h in headers]
    
    # Infer basic dtypes based on first row
    dtypes = {}
    preview = []
    
    for row in rows:
        row_dict = {}
        for col, val in zip(columns, row):
            # Attempt to convert to infer type
            try:
                # Try int
                val_int = int(val)
                dtypes[col] = "int64"
                row_dict[col] = val_int
            except ValueError:
                try:
                    # Try float
                    val_float = float(val)
                    dtypes[col] = "float64"
                    row_dict[col] = val_float
                except ValueError:
                    # Fallback string
                    dtypes[col] = "object"
                    row_dict[col] = val
        preview.append(row_dict)

    # Any columns missing from first row get object
    for c in columns:
        if c not in dtypes:
            dtypes[c] = "object"

    return {
        "columns": columns,
        "row_count": row_count,
        "dtypes": dtypes,
        "preview": preview,
    }
