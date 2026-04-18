"""
test_contract.py — Validate all Person 2 API endpoints against CONTRACT.md

Tests:
  1. POST /api/v1/analyze/run
  2. GET  /api/v1/results/{job_id}
  3. POST /api/v1/remediate/reweigh
  4. GET  /api/v1/remediate/threshold
  5. Validates results_local.json against CONTRACT.md schema
  6. Stub endpoints (upload, explain, report)
"""

import json
import sys
import time
import requests

BASE = "http://127.0.0.1:8000/api/v1"
PASS = "[PASS]"
FAIL = "[FAIL]"
WARN = "[WARN]"

results = []

def check(condition, label, detail=""):
    icon = PASS if condition else FAIL
    results.append((icon, label))
    print(f"  {icon} {label}")
    if detail and not condition:
        print(f"       -> {detail}")
    return condition


def banner(title):
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}")


# ─────────────────────────────────────────────────────────
# CONTRACT SCHEMA DEFINITIONS (from CONTRACT.md Section 4 & 6)
# ─────────────────────────────────────────────────────────

RESULTS_TOP_LEVEL_KEYS = {
    "job_id", "completed_at", "dataset_info", "metrics",
    "per_group_stats", "overall_severity", "metrics_passed",
    "metrics_failed", "shap", "remediation"
}

METRIC_NAMES = {
    "disparate_impact", "demographic_parity_difference",
    "equalized_odds_difference", "calibration_difference"
}

METRIC_FIELDS = {"value", "threshold", "passed", "description"}
METRIC_AFTER_FIELDS = {"value", "passed"}

DATASET_INFO_FIELDS = {
    "total_rows", "target_column", "protected_attributes",
    "positive_rate_overall"
}

PER_GROUP_STAT_FIELDS = {"count", "positive_rate", "tpr", "fpr"}

SHAP_TOP_FEATURE_FIELDS = {"feature", "importance", "direction"}
VALID_DIRECTIONS = {"positive", "negative", "mixed"}

VALID_SEVERITIES = {"high", "medium", "low", "none"}

THRESHOLD_RESPONSE_FIELDS = {"threshold", "accuracy", "per_group",
                              "demographic_parity_difference",
                              "equalized_odds_difference"}

THRESHOLD_GROUP_FIELDS = {"tpr", "fpr", "positive_rate"}


# ─────────────────────────────────────────────────────────
# STEP 0 — Validate results_local.json (offline schema check)
# ─────────────────────────────────────────────────────────
banner("STEP 0 — Validate artifacts/results_local.json against CONTRACT.md")

try:
    with open("./artifacts/results_local.json") as f:
        local_results = json.load(f)

    # Top-level keys
    for key in RESULTS_TOP_LEVEL_KEYS:
        check(key in local_results, f"results.json has top-level key: '{key}'",
              f"Missing key: {key}")

    extra_keys = set(local_results.keys()) - RESULTS_TOP_LEVEL_KEYS
    check(len(extra_keys) == 0, f"No extra top-level keys",
          f"Extra keys: {extra_keys}")

    # dataset_info
    di = local_results.get("dataset_info", {})
    for field in DATASET_INFO_FIELDS:
        check(field in di, f"dataset_info.{field} present")

    check(isinstance(di.get("total_rows"), int), "dataset_info.total_rows is int")
    check(isinstance(di.get("target_column"), str), "dataset_info.target_column is str")
    check(isinstance(di.get("protected_attributes"), list), "dataset_info.protected_attributes is list")
    check(isinstance(di.get("positive_rate_overall"), (int, float)), "dataset_info.positive_rate_overall is numeric")

    # metrics
    metrics = local_results.get("metrics", {})
    check(set(metrics.keys()) == METRIC_NAMES, "metrics has exactly 4 required metrics",
          f"Got: {set(metrics.keys())}")

    for mname, mdata in metrics.items():
        for field in METRIC_FIELDS:
            check(field in mdata, f"metrics.{mname}.{field} present")
        check(isinstance(mdata.get("value"), (int, float)), f"metrics.{mname}.value is numeric")
        check(isinstance(mdata.get("threshold"), (int, float)), f"metrics.{mname}.threshold is numeric")
        check(isinstance(mdata.get("passed"), bool), f"metrics.{mname}.passed is bool")
        check(isinstance(mdata.get("description"), str), f"metrics.{mname}.description is str")
        # Check rounding (<=3 decimal places)
        val_str = str(mdata.get("value", 0))
        if "." in val_str:
            decimals = len(val_str.split(".")[-1])
            check(decimals <= 3, f"metrics.{mname}.value rounded to <=3 decimals",
                  f"Got {decimals} decimals: {mdata['value']}")

    # per_group_stats
    pgs = local_results.get("per_group_stats", {})
    prot_attrs = di.get("protected_attributes", [])
    for attr in prot_attrs:
        check(attr in pgs, f"per_group_stats has '{attr}'")
        if attr in pgs:
            for group_name, group_data in pgs[attr].items():
                for field in PER_GROUP_STAT_FIELDS:
                    check(field in group_data, f"per_group_stats.{attr}.{group_name}.{field} present")

    # severity
    severity = local_results.get("overall_severity")
    check(severity in VALID_SEVERITIES, f"overall_severity is valid: '{severity}'")

    # metrics_passed + metrics_failed
    mp = local_results.get("metrics_passed", 0)
    mf = local_results.get("metrics_failed", 0)
    check(mp + mf == 4, f"metrics_passed({mp}) + metrics_failed({mf}) == 4")

    # Severity logic validation
    if mf >= 2:
        check(severity == "high", f"Severity should be 'high' when {mf} metrics failed")
    elif mf == 1:
        check(severity == "medium", f"Severity should be 'medium' when 1 metric failed")
    elif mf == 0:
        check(severity in {"low", "none"}, f"Severity should be 'low'/'none' when 0 metrics failed")

    # shap block
    shap = local_results.get("shap", {})
    check("top_features" in shap, "shap.top_features present")
    check("protected_attr_shap" in shap, "shap.protected_attr_shap present")
    check("note" in shap, "shap.note present")

    top_feats = shap.get("top_features", [])
    check(len(top_feats) > 0, f"shap.top_features is non-empty ({len(top_feats)} features)")

    for i, feat in enumerate(top_feats):
        for field in SHAP_TOP_FEATURE_FIELDS:
            check(field in feat, f"shap.top_features[{i}].{field} present")
        check(feat.get("direction") in VALID_DIRECTIONS,
              f"shap.top_features[{i}].direction is valid: '{feat.get('direction')}'")
        check(isinstance(feat.get("importance"), (int, float)),
              f"shap.top_features[{i}].importance is numeric")

    pashap = shap.get("protected_attr_shap", {})
    for attr in prot_attrs:
        check(attr in pashap, f"shap.protected_attr_shap has '{attr}'")

    # remediation block
    rem = local_results.get("remediation", {})
    check("reweighing" in rem, "remediation.reweighing present")
    check("threshold" in rem, "remediation.threshold present")

    rw = rem.get("reweighing", {})
    check("applied" in rw, "remediation.reweighing.applied present")
    check(isinstance(rw.get("applied"), bool), "remediation.reweighing.applied is bool")

    if rw.get("applied"):
        check("metrics_after" in rw, "remediation.reweighing.metrics_after present")
        check("accuracy_before" in rw, "remediation.reweighing.accuracy_before present")
        check("accuracy_after" in rw, "remediation.reweighing.accuracy_after present")
        check("accuracy_delta" in rw, "remediation.reweighing.accuracy_delta present")

        ma = rw.get("metrics_after", {})
        check(set(ma.keys()) == METRIC_NAMES, "metrics_after has exactly 4 metrics",
              f"Got: {set(ma.keys())}")
        for mname, mdata in ma.items():
            for field in METRIC_AFTER_FIELDS:
                check(field in mdata, f"metrics_after.{mname}.{field} present")

    thr = rem.get("threshold", {})
    check("current_threshold" in thr, "remediation.threshold.current_threshold present")
    check("privileged_group" in thr, "remediation.threshold.privileged_group present")
    check("unprivileged_group" in thr, "remediation.threshold.unprivileged_group present")

except FileNotFoundError:
    check(False, "artifacts/results_local.json exists")


# ─────────────────────────────────────────────────────────
# STEP 1 — POST /analyze/run (Contract Section 6)
# ─────────────────────────────────────────────────────────
banner("STEP 1 — POST /api/v1/analyze/run")

# First, we need data.csv in artifacts. Create it from predictions.csv context
import pandas as pd

# Download Adult Income dataset to create data.csv
print("  Preparing: Downloading data.csv for /analyze/run test...")
columns = [
    "age", "workclass", "fnlwgt", "education", "education_num",
    "marital_status", "occupation", "relationship", "race", "sex",
    "capital_gain", "capital_loss", "hours_per_week", "native_country", "income",
]
url_data = "https://archive.ics.uci.edu/ml/machine-learning-databases/adult/adult.data"
df = pd.read_csv(url_data, names=columns, skipinitialspace=True)
for col in df.select_dtypes(include=["object", "string"]).columns:
    df[col] = df[col].str.strip()
df["income"] = df["income"].apply(lambda x: 1 if ">50K" in str(x) else 0)
df.to_csv("./artifacts/data.csv", index=False)
print("  Preparing: data.csv written to artifacts/")

# Also create config.json
config = {
    "job_id": "test-contract-001",
    "target_column": "income",
    "protected_attributes": ["sex", "race"],
    "positive_outcome_label": 1,
}
with open("./artifacts/config.json", "w") as f:
    json.dump(config, f)
print("  Preparing: config.json written to artifacts/")

# Contract: Input = {job_id}, Output = {job_id, status: "queued"}  (implied from route table)
r = requests.post(f"{BASE}/analyze/run", json={"job_id": "test-contract-001"})
check(r.status_code == 200, f"POST /analyze/run returns 200 (got {r.status_code})")

data = r.json()
check("job_id" in data, "Response has 'job_id'")
check("status" in data, "Response has 'status'")
check(data.get("status") == "queued", f"status == 'queued' (got '{data.get('status')}')")
check("message" in data, "Response has 'message'")

# Wait for background task to complete
print("  Waiting 15s for background analysis to finish...")
time.sleep(15)


# ─────────────────────────────────────────────────────────
# STEP 2 — GET /results/{job_id} (Contract Section 6)
# ─────────────────────────────────────────────────────────
banner("STEP 2 — GET /api/v1/results/{job_id}")

r = requests.get(f"{BASE}/results/test-contract-001")
check(r.status_code == 200, f"GET /results/test-contract-001 returns 200 (got {r.status_code})")

if r.status_code == 200:
    api_results = r.json()

    # Validate against full CONTRACT.md results.json schema
    for key in RESULTS_TOP_LEVEL_KEYS:
        check(key in api_results, f"API results has top-level key: '{key}'")

    api_extra = set(api_results.keys()) - RESULTS_TOP_LEVEL_KEYS
    check(len(api_extra) == 0, f"No extra top-level keys in API results",
          f"Extra: {api_extra}")

    # Check job_id matches
    check(api_results.get("job_id") == "test-contract-001",
          f"job_id matches request (got '{api_results.get('job_id')}')")

    # Check completed_at is ISO8601
    check(isinstance(api_results.get("completed_at"), str),
          "completed_at is a string (ISO8601)")

    # Check metric structure
    api_metrics = api_results.get("metrics", {})
    check(set(api_metrics.keys()) == METRIC_NAMES,
          "API results has all 4 required metrics")

    # Check shap structure
    api_shap = api_results.get("shap", {})
    check("top_features" in api_shap, "API shap.top_features present")
    check("protected_attr_shap" in api_shap, "API shap.protected_attr_shap present")

    # Check remediation structure
    api_rem = api_results.get("remediation", {})
    check("reweighing" in api_rem, "API remediation.reweighing present")
    check("threshold" in api_rem, "API remediation.threshold present")

    api_thr = api_rem.get("threshold", {})
    check("current_threshold" in api_thr, "API remediation.threshold.current_threshold present")
    check("privileged_group" in api_thr, "API remediation.threshold.privileged_group present")
    check("unprivileged_group" in api_thr, "API remediation.threshold.unprivileged_group present")
else:
    print("  Skipping results schema checks — endpoint returned error")


# ─────────────────────────────────────────────────────────
# STEP 3 — GET /results/{job_id} with invalid job_id
# ─────────────────────────────────────────────────────────
banner("STEP 3 — GET /api/v1/results/{invalid_job_id} (error case)")

r = requests.get(f"{BASE}/results/nonexistent-job-999")
check(r.status_code == 404, f"Returns 404 for missing job (got {r.status_code})")


# ─────────────────────────────────────────────────────────
# STEP 4 — POST /remediate/reweigh (Contract Section 6)
# ─────────────────────────────────────────────────────────
banner("STEP 4 — POST /api/v1/remediate/reweigh")

# Contract: Input = {job_id}, Output = updated results with reweighing applied
r = requests.post(f"{BASE}/remediate/reweigh", json={"job_id": "test-contract-001"})
check(r.status_code == 200, f"POST /remediate/reweigh returns 200 (got {r.status_code})")

if r.status_code == 200:
    rw_data = r.json()

    # Should return full updated results
    for key in RESULTS_TOP_LEVEL_KEYS:
        check(key in rw_data, f"Reweigh response has top-level key: '{key}'")

    rw_rem = rw_data.get("remediation", {}).get("reweighing", {})
    check(rw_rem.get("applied") == True, "reweighing.applied is True")
    check("metrics_after" in rw_rem, "reweighing.metrics_after present in response")
    check("accuracy_before" in rw_rem, "reweighing.accuracy_before present")
    check("accuracy_after" in rw_rem, "reweighing.accuracy_after present")
    check("accuracy_delta" in rw_rem, "reweighing.accuracy_delta present")

    # Validate metrics_after has all 4 metrics
    if "metrics_after" in rw_rem:
        ma = rw_rem["metrics_after"]
        check(set(ma.keys()) == METRIC_NAMES, "metrics_after has all 4 metrics")
        for mname, mdata in ma.items():
            check("value" in mdata, f"metrics_after.{mname}.value present")
            check("passed" in mdata, f"metrics_after.{mname}.passed present")
else:
    print("  Skipping reweigh checks — endpoint returned error")
    if r.status_code != 200:
        print(f"  Response: {r.text[:500]}")


# ─────────────────────────────────────────────────────────
# STEP 5 — GET /remediate/threshold (Contract Section 6)
# ─────────────────────────────────────────────────────────
banner("STEP 5 — GET /api/v1/remediate/threshold")

# Contract: Input = ?job_id=x&threshold=0.6
# Output = {metrics_at_threshold, accuracy} — inferred as {threshold, accuracy, per_group, dpd, eod}
r = requests.get(f"{BASE}/remediate/threshold",
                 params={"job_id": "test-contract-001", "threshold": 0.6, "protected": "sex"})
check(r.status_code == 200, f"GET /remediate/threshold returns 200 (got {r.status_code})")

if r.status_code == 200:
    thr_data = r.json()

    for field in THRESHOLD_RESPONSE_FIELDS:
        check(field in thr_data, f"Threshold response has '{field}'")

    check(isinstance(thr_data.get("threshold"), (int, float)), "threshold is numeric")
    check(thr_data.get("threshold") == 0.6, f"threshold matches request (got {thr_data.get('threshold')})")
    check(isinstance(thr_data.get("accuracy"), (int, float)), "accuracy is numeric")
    check(0 <= thr_data.get("accuracy", -1) <= 1, "accuracy is between 0 and 1")

    pg = thr_data.get("per_group", {})
    check(len(pg) > 0, f"per_group is non-empty ({len(pg)} groups)")
    for group_name, group_data in pg.items():
        for field in THRESHOLD_GROUP_FIELDS:
            check(field in group_data, f"per_group.{group_name}.{field} present")

    check(isinstance(thr_data.get("demographic_parity_difference"), (int, float)),
          "demographic_parity_difference is numeric")
    check(isinstance(thr_data.get("equalized_odds_difference"), (int, float)),
          "equalized_odds_difference is numeric")

    # Test latency — Contract says < 200ms
    if "latency_ms" in thr_data:
        latency = thr_data["latency_ms"]
        check(latency < 200, f"Latency < 200ms (got {latency}ms)")
else:
    print("  Skipping threshold checks — endpoint returned error")
    print(f"  Response: {r.text[:500]}")


# Test multiple thresholds
banner("STEP 5b — Threshold sweep (latency validation)")
all_fast = True
for t in [0.3, 0.4, 0.5, 0.6, 0.7]:
    start = time.time()
    r = requests.get(f"{BASE}/remediate/threshold",
                     params={"job_id": "test-contract-001", "threshold": t, "protected": "sex"})
    elapsed = (time.time() - start) * 1000
    if r.status_code == 200:
        d = r.json()
        server_latency = d.get("latency_ms", "N/A")
        print(f"  t={t}: accuracy={d['accuracy']}, dpd={d['demographic_parity_difference']}, "
              f"eod={d['equalized_odds_difference']}, server={server_latency}ms, total={elapsed:.0f}ms")
        if isinstance(server_latency, (int, float)) and server_latency > 200:
            all_fast = False
    else:
        all_fast = False
        print(f"  t={t}: ERROR {r.status_code}")

check(all_fast, "All threshold calls < 200ms server-side")


# ─────────────────────────────────────────────────────────
# STEP 6 — Validate threshold error cases
# ─────────────────────────────────────────────────────────
banner("STEP 6 — Threshold error cases")

r = requests.get(f"{BASE}/remediate/threshold",
                 params={"job_id": "nonexistent-job", "threshold": 0.5})
check(r.status_code in [404, 422], f"Missing job returns 404/422 (got {r.status_code})")


# ─────────────────────────────────────────────────────────
# STEP 7 — Stub endpoints (Person 1 & 3 stubs)
# ─────────────────────────────────────────────────────────
banner("STEP 7 — Stub endpoints (should respond without crashing)")

# Upload stubs
r = requests.post(f"{BASE}/upload/csv")
check(r.status_code == 200, f"POST /upload/csv stub responds (got {r.status_code})")

r = requests.post(f"{BASE}/upload/model")
check(r.status_code == 200, f"POST /upload/model stub responds (got {r.status_code})")

r = requests.post(f"{BASE}/analyze/configure")
check(r.status_code == 200, f"POST /analyze/configure stub responds (got {r.status_code})")

r = requests.get(f"{BASE}/status/test-123")
check(r.status_code == 200, f"GET /status/test-123 stub responds (got {r.status_code})")

# Explain stubs
r = requests.post(f"{BASE}/explain", json={"job_id": "test"})
check(r.status_code == 200, f"POST /explain stub responds (got {r.status_code})")

r = requests.post(f"{BASE}/ask", json={"job_id": "test", "question": "Why?"})
check(r.status_code == 200, f"POST /ask stub responds (got {r.status_code})")

# Report stub
r = requests.get(f"{BASE}/report/test-123")
check(r.status_code == 200, f"GET /report/test-123 stub responds (got {r.status_code})")


# ─────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────
banner("FINAL SUMMARY")

passed = sum(1 for icon, _ in results if icon == PASS)
failed = sum(1 for icon, _ in results if icon == FAIL)
total = len(results)

print(f"\n  Total checks : {total}")
print(f"  Passed       : {passed}")
print(f"  Failed       : {failed}")

if failed > 0:
    print(f"\n  FAILURES:")
    for icon, label in results:
        if icon == FAIL:
            print(f"    {FAIL} {label}")

print(f"\n{'=' * 70}")
if failed == 0:
    print("  ALL CHECKS PASSED -- Contract compliance verified!")
else:
    print(f"  {failed} CHECK(S) FAILED -- Review above failures")
print(f"{'=' * 70}\n")

sys.exit(1 if failed > 0 else 0)
