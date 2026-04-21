"""
services/gemini.py
==================
Standalone Gemini API client. Uses Python stdlib urllib only — no SDK.

Iterates through a preferred model list, skipping any model that:
  - returns 404 (not available for this key)
  - returns 429 with limit: 0 (paid-only model, no free tier quota)
This means it will automatically find the first model that actually works.

Required env var:
    GEMINI_API_KEY   — free key from https://aistudio.google.com/apikey

Optional env var:
    GEMINI_MODEL     — force a specific model (skips auto-detection)
"""

import json
import logging
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_BASE = "https://generativelanguage.googleapis.com/v1beta"

# Ordered by preference — free-tier models first, paid-only last.
# The code tries each in order and skips those that are unavailable.
_PREFERRED = [
    "gemini-2.5-flash",
    "gemini-flash-latest",
    "gemma-3-27b-it",
    "gemma-3-12b-it",
    "gemini-2.0-flash",
]

_working_model: str | None = None  # cached after first successful call


# ── private ────────────────────────────────────────────────────────────────────

def _key() -> str:
    k = os.getenv("GEMINI_API_KEY", "").strip()
    if not k:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. "
            "Get a free key at https://aistudio.google.com/apikey"
        )
    return k


def _http_post(url: str, body: dict, timeout: int = 120) -> dict:
    payload = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Gemini HTTP {e.code}: {err}") from e


def _call_model(model: str, key: str, contents: list, system: str = None,
                max_tokens: int = 4096, temperature: float = 0.2) -> str:
    """Call a specific model. Raises RuntimeError on any failure."""
    url = f"{_BASE}/models/{model}:generateContent?key={key}"
    body: dict = {
        "contents": contents,
        "generationConfig": {"maxOutputTokens": max_tokens, "temperature": temperature},
    }
    if system:
        body["system_instruction"] = {"parts": [{"text": system}]}

    data = _http_post(url, body)
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as exc:
        raise RuntimeError(f"Unexpected response shape: {data}") from exc


def _is_no_quota(error_msg: str) -> bool:
    """Return True if the error means the model has zero quota (paid-only)."""
    return "limit: 0" in error_msg or '"limit":0' in error_msg


def _is_not_found(error_msg: str) -> bool:
    return "HTTP 404" in error_msg or "not found" in error_msg.lower()

def _is_unavailable(error_msg: str) -> bool:
    return "HTTP 503" in error_msg or "unavailable" in error_msg.lower()

def _is_rate_limited(error_msg: str) -> bool:
    """Return True if the error is a normal per-minute rate limit (not limit: 0)."""
    return ("429" in error_msg or "quota" in error_msg.lower()) and not _is_no_quota(error_msg)


def _generate(
    contents: list,
    system: str = None,
    max_tokens: int = 4096,
    temperature: float = 0.2,
) -> str:
    """
    Try each model in _PREFERRED until one works.
    Skips models that are not found (404) or have zero quota (limit: 0).
    Waits and retries on per-minute rate limits.
    Caches the working model for subsequent calls.
    """
    global _working_model

    key = _key()

    # If a model is manually configured, use only that one.
    override = os.getenv("GEMINI_MODEL", "").strip()
    if override:
        return _call_model(override, key, contents, system=system,
                           max_tokens=max_tokens, temperature=temperature)

    # If we already found a working model this session, start with it.
    model_list = _PREFERRED
    if _working_model:
        # Put the cached model first so we use it immediately
        rest = [m for m in _PREFERRED if m != _working_model]
        model_list = [_working_model] + rest

    last_err = None
    for model in model_list:
        try:
            text = _call_model(model, key, contents, system=system,
                               max_tokens=max_tokens, temperature=temperature)
            if _working_model != model:
                logger.info(f"Gemini: using model '{model}'")
                _working_model = model
            return text

        except RuntimeError as exc:
            msg = str(exc)
            if _is_not_found(msg):
                logger.debug(f"Model '{model}' not available (404), trying next…")
                continue
            elif _is_no_quota(msg):
                logger.debug(f"Model '{model}' has no quota (limit: 0), trying next…")
                continue
            elif _is_unavailable(msg):
                logger.warning(f"Model '{model}' is unavailable (503), trying next…")
                last_err = exc
                continue
            elif _is_rate_limited(msg):
                # Per-minute limit — wait, then retry once before moving on
                wait = 30
                logger.warning(f"Model '{model}' rate-limited. Waiting {wait}s then retrying…")
                time.sleep(wait)
                try:
                    text = _call_model(model, key, contents, system=system,
                                       max_tokens=max_tokens, temperature=temperature)
                    _working_model = model
                    return text
                except RuntimeError as retry_exc:
                    last_err = retry_exc
                    logger.warning(f"Model '{model}' still failing after wait: {retry_exc}")
                    continue
            else:
                raise  # real non-quota error — don't swallow it

        except Exception as exc:
            raise RuntimeError(f"Unexpected error calling '{model}': {exc}") from exc

    raise RuntimeError(
        f"All Gemini models exhausted — none worked for this API key. "
        f"Last error: {last_err}"
    )


def _parse_json(raw: str, fallback_prompt: str) -> dict:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        cleaned = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    logger.warning("JSON parse failed — retrying with explicit JSON instruction")
    retry_contents = [{"role": "user", "parts": [
        {"text": fallback_prompt + "\n\nReturn ONLY valid JSON. No markdown fences."}
    ]}]
    raw2 = _generate(retry_contents, max_tokens=4096)
    cleaned2 = raw2.strip()
    if cleaned2.startswith("```"):
        lines = cleaned2.split("\n")
        cleaned2 = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    try:
        return json.loads(cleaned2)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Gemini did not return valid JSON. Raw: {raw[:400]}") from exc


# ── Public API ─────────────────────────────────────────────────────────────────

def generate_explanation(results: dict, job_id: str) -> dict:
    """
    Analyse bias audit results with Gemini and return a structured explanation dict.
    Saved as explanation.json by the caller.
    """
    from prompts.gemini_prompt import SYSTEM_PROMPT, build_analysis_prompt

    prompt = build_analysis_prompt(results)
    contents = [{"role": "user", "parts": [{"text": prompt}]}]

    logger.info(f"Requesting Gemini explanation for job {job_id}")
    raw = _generate(contents, system=SYSTEM_PROMPT, max_tokens=4096)
    parsed = _parse_json(raw, fallback_prompt=prompt)

    return {
        "job_id": job_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": parsed.get("summary", ""),
        "severity_label": parsed.get(
            "severity_label",
            results.get("overall_severity", "unknown").title() + " bias detected",
        ),
        "findings": parsed.get("findings", []),
        "recommended_fix": parsed.get("recommended_fix", "none"),
        "recommended_fix_reason": parsed.get("recommended_fix_reason", ""),
        "plain_english": parsed.get("plain_english") or parsed.get("summary", ""),
    }


def answer_question(messages: list, system: str = None, max_tokens: int = 512) -> str:
    """Multi-turn Q&A for the /ask endpoint."""
    contents = [
        {"role": m["role"], "parts": m["parts"]}
        for m in messages
    ]
    return _generate(contents, system=system, max_tokens=max_tokens, temperature=0.3)
