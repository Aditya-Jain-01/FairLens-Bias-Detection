"""
services/pii_detector.py
========================
Scans a list of column names (and optionally sample values) for likely
Personally Identifiable Information (PII) patterns.

Used by the upload router to return a warning to the frontend when
sensitive columns are detected BEFORE analysis begins.

Detection strategy:
  1. Keyword match on column name (fast, zero-cost)
  2. Regex pattern match on up to 5 sample values (lightweight)

Returns:
  {
    "has_pii": bool,
    "flagged_columns": [{"column": "email", "reason": "Email address pattern", "risk": "high"}, ...]
  }
"""

import re
import logging
from typing import Any, Optional, Dict, List, Set

logger = logging.getLogger(__name__)

# ── Keyword rules (column name matching, case-insensitive) ────────────────────

_KEYWORD_RULES: List[tuple] = [
    # (keywords, reason, risk)
    (["email", "e-mail", "mail"],               "Email address",           "high"),
    (["phone", "mobile", "cell", "tel"],         "Phone number",            "high"),
    (["ssn", "social_security", "sin", "nino"],  "Government ID number",    "critical"),
    (["passport", "passport_no", "passport_num"],"Passport number",         "critical"),
    (["dob", "date_of_birth", "birthdate", "birthday"], "Date of birth",    "high"),
    (["name", "first_name", "last_name", "surname", "fullname", "full_name"], "Person name", "medium"),
    (["address", "street", "city", "postcode", "zip", "zipcode"],            "Location/address", "medium"),
    (["ip", "ip_address", "ipaddr"],             "IP address",              "medium"),
    (["credit_card", "card_number", "cc_num"],   "Credit card number",      "critical"),
    (["salary", "income", "wage", "earnings"],   "Financial data",          "medium"),
    (["license", "licence", "dl", "driver"],     "Driver's license",        "high"),
    (["nhs", "health_id", "patient_id", "mrn"],  "Medical identifier",      "critical"),
    (["national_id", "national_number", "nin"],  "National identity number", "critical"),
]

# ── Value-level regex patterns ────────────────────────────────────────────────

_VALUE_PATTERNS: List[tuple] = [
    (re.compile(r"^[\w.+-]+@[\w-]+\.[a-z]{2,}$", re.I),             "Email address pattern",      "high"),
    (re.compile(r"^\+?[\d\s\-().]{7,15}$"),                           "Phone number pattern",       "high"),
    (re.compile(r"^\d{3}-\d{2}-\d{4}$"),                              "SSN pattern (US)",           "critical"),
    (re.compile(r"^\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}$"),       "Credit card pattern",        "critical"),
    (re.compile(r"^\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}$"),            "Date of birth pattern",      "high"),
    (re.compile(r"^(?:\d{1,3}\.){3}\d{1,3}$"),                       "IP address pattern",         "medium"),
]


def detect_pii(columns: List[str], sample_values: Optional[Dict[str, List[Any]]] = None) -> dict:
    """
    Scan column names and optional sample values for PII signals.

    Args:
        columns:      List of column name strings from the uploaded CSV.
        sample_values: Optional dict mapping column_name -> list of up to 5 sample values.

    Returns:
        {"has_pii": bool, "flagged_columns": [...]}
    """
    flagged: List[dict] = []
    seen_columns: Set[str] = set()

    for col in columns:
        col_lower = col.lower().replace(" ", "_").replace("-", "_")

        # 1. Keyword match
        for keywords, reason, risk in _KEYWORD_RULES:
            if any(kw in col_lower for kw in keywords):
                if col not in seen_columns:
                    flagged.append({"column": col, "reason": reason, "risk": risk})
                    seen_columns.add(col)
                break

        # 2. Value-level pattern match (only if column not already flagged)
        if col not in seen_columns and sample_values and col in sample_values:
            for val in sample_values[col][:5]:
                val_str = str(val).strip()
                for pattern, reason, risk in _VALUE_PATTERNS:
                    if pattern.match(val_str):
                        flagged.append({"column": col, "reason": reason, "risk": risk})
                        seen_columns.add(col)
                        break
                if col in seen_columns:
                    break

    return {
        "has_pii": len(flagged) > 0,
        "flagged_columns": flagged,
    }
