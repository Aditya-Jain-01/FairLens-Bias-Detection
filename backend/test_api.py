#!/usr/bin/env python3
"""
test_api.py — Quick smoke-test for all backend endpoints.
Run AFTER starting the server: uvicorn main:app --reload

Usage:
    python3 test_api.py                     # test against localhost:8000
    python3 test_api.py https://my-url.run  # test against Cloud Run
"""

import sys
import json
import time
import tempfile
import os

try:
    import urllib.request as req
    import urllib.error
    import urllib.parse
except ImportError:
    pass

BASE = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://localhost:8000"
API  = f"{BASE}/api/v1"

PASS = "✅"
FAIL = "❌"
results = []


def check(name: str, ok: bool, detail: str = ""):
    icon = PASS if ok else FAIL
    msg = f"  {icon} {name}"
    if detail:
        msg += f" — {detail}"
    print(msg)
    results.append(ok)


def get(path: str) -> tuple[int, dict]:
    url = f"{API}{path}"
    try:
        with req.urlopen(url, timeout=10) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, {}
    except Exception as e:
        return 0, {"error": str(e)}


def post_json(path: str, data: dict) -> tuple[int, dict]:
    url = f"{API}{path}"
    body = json.dumps(data).encode()
    r2 = req.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with req.urlopen(r2, timeout=10) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, {}
    except Exception as e:
        return 0, {"error": str(e)}


def post_multipart(path: str, fields: dict, files: dict) -> tuple[int, dict]:
    """Minimal multipart/form-data POST."""
    boundary = "----FairLensBoundary"
    body_parts = []
    for k, v in fields.items():
        body_parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}'.encode()
        )
    for k, (fname, content, ctype) in files.items():
        body_parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"; filename="{fname}"\r\nContent-Type: {ctype}\r\n\r\n'.encode()
            + content
        )
    body = b"\r\n".join(body_parts) + f"\r\n--{boundary}--\r\n".encode()
    url = f"{API}{path}"
    r2 = req.Request(
        url, data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    try:
        with req.urlopen(r2, timeout=15) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        body2 = e.read()
        try:
            return e.code, json.loads(body2)
        except Exception:
            return e.code, {"raw": body2.decode(errors="replace")}
    except Exception as e:
        return 0, {"error": str(e)}


# ── CSV content ───────────────────────────────────────────────────────────────
SAMPLE_CSV = b"""age,gender,race,education_num,capital_gain,hours_per_week,income
39,Male,White,13,2174,40,1
50,Male,White,13,0,13,0
38,Male,White,9,0,40,0
53,Male,Black,7,0,40,0
28,Female,Black,13,0,40,0
37,Female,White,14,0,40,1
49,Female,Other,5,0,16,0
52,Male,White,9,0,45,0
31,Female,White,14,14084,50,1
42,Male,White,13,5178,40,1
"""


# ═══════════════════════════════════════════════════════════════════════════════
print(f"\n{'='*55}")
print(f"  FairLens API Smoke Tests")
print(f"  Target: {BASE}")
print(f"{'='*55}\n")

# 1. Health
print("── Infra ──")
code, data = get("/health".replace("/api/v1", "").replace("//", "/"))
# health is at /health not /api/v1/health
url = f"{BASE}/health"
try:
    with req.urlopen(url, timeout=5) as r:
        code, data = r.status, json.loads(r.read())
except Exception as e:
    code, data = 0, {"error": str(e)}
check("GET /health", code == 200, data.get("status", ""))

# Root
url = BASE
try:
    with req.urlopen(url, timeout=5) as r:
        code, data = r.status, json.loads(r.read())
except Exception as e:
    code, data = 0, {}
check("GET /", code == 200)

# 2. CSV Upload
print("\n── Upload ──")
code, data = post_multipart(
    "/upload/csv",
    fields={},
    files={"file": ("test.csv", SAMPLE_CSV, "text/csv")},
)
check("POST /upload/csv", code == 200, f"job_id={data.get('job_id','?')[:8]}...")
job_id = data.get("job_id", "")
columns = data.get("columns", [])
check("CSV returns columns", bool(columns), str(columns[:3]))
check("CSV returns row_count", "row_count" in data, str(data.get("row_count")))

# 3. Model upload (with a tiny fake pkl)
if job_id:
    import pickle
    from sklearn.dummy import DummyClassifier
    import numpy as np
    
    # Create a real but tiny model so the server can unpickle it
    clf = DummyClassifier(strategy="constant", constant=1)
    y_dummy = np.zeros(10)
    y_dummy[0] = 1 # inject at least one positive class
    clf.fit(np.zeros((10, 2)), y_dummy)
    fake_model = pickle.dumps(clf)
    code2, data2 = post_multipart(
        "/upload/model",
        fields={"job_id": job_id},
        files={"file": ("model.pkl", fake_model, "application/octet-stream")},
    )
    check("POST /upload/model", code2 == 200, f"model_type={data2.get('model_type','?')}")

# 4. Configure
print("\n── Analyze ──")
if job_id and columns:
    target = columns[-1]  # income
    protected = [c for c in columns if c in ("gender", "race", "sex")]
    if not protected:
        protected = [columns[1]]
    code3, data3 = post_json("/analyze/configure", {
        "job_id": job_id,
        "target_column": target,
        "protected_attributes": protected,
        "positive_outcome_label": 1,
    })
    check("POST /analyze/configure", code3 == 200, data3.get("status", ""))

# 5. Status polling
print("\n── Status ──")
if job_id:
    time.sleep(0.5)
    code4, data4 = get(f"/status/{job_id}")
    check("GET /status/{job_id}", code4 == 200, f"stage={data4.get('stage','?')}")
    check("Status has progress", "progress" in data4, str(data4.get("progress")))

# 6. Status for unknown job
code5, data5 = get("/status/nonexistent-job-id")
check("GET /status/{bad_id} returns error stage", data5.get("stage") == "error")

# 7. Demo job
print("\n── Demo ──")
code6, data6 = post_json("/analyze/configure", {
    "job_id": "demo",
    "target_column": "income",
    "protected_attributes": ["gender", "race"],
    "positive_outcome_label": 1,
})
check("POST /analyze/configure (demo)", code6 == 200)
time.sleep(0.3)
code7, data7 = get("/status/demo")
check("GET /status/demo", code7 == 200, f"stage={data7.get('stage','?')}")

# 8. Stub endpoints
print("\n── Stub endpoints ──")
code8, _ = get("/remediate/threshold?job_id=demo&threshold=0.6")
check("GET /remediate/threshold (stub)", code8 == 200)

code9, _ = get("/report/demo")
check("GET /report/{job_id} (stub)", code9 == 200)

# ── Summary ────────────────────────────────────────────────────────────────
total = len(results)
passed = sum(results)
print(f"\n{'='*55}")
print(f"  {passed}/{total} tests passed")
if passed == total:
    print("  🎉 All good! Server is working correctly.")
else:
    print(f"  ⚠️  {total - passed} test(s) failed. Check server logs.")
print(f"{'='*55}\n")
sys.exit(0 if passed == total else 1)
