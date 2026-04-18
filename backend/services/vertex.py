"""
FairLens — Gemini Client Wrapper

Supports two authentication modes (in priority order):
  1. GEMINI_API_KEY  — Google AI Studio key (aistudio.google.com/apikey)
                       Simpler, works without Vertex AI setup.
  2. GCP_PROJECT_ID  — Vertex AI / Application Default Credentials
                       Used on Cloud Run with service account roles.

Set exactly one of these in your environment / Cloud Run env vars.
"""

import os
import time
import json
import logging
from typing import Generator

logger = logging.getLogger(__name__)

_initialized = False
_vertex_available = False
_use_api_key = False   # True when using google-generativeai (GEMINI_API_KEY mode)


def _ensure_init() -> None:
    """Lazily initialise Gemini once per process."""
    global _initialized, _vertex_available, _use_api_key
    if _initialized:
        return

    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        try:
            import google.generativeai as genai  # type: ignore
            genai.configure(api_key=api_key)
            _vertex_available = True
            _use_api_key = True
            logger.info("Gemini initialised via GEMINI_API_KEY (Google AI Studio mode)")
        except ImportError:
            logger.warning("google-generativeai package not installed — install it or use Vertex AI")
    else:
        project = os.getenv("GCP_PROJECT_ID")
        location = os.getenv("VERTEX_AI_LOCATION", "us-central1")
        if project:
            try:
                import vertexai  # type: ignore
                vertexai.init(project=project, location=location)
                _vertex_available = True
                _use_api_key = False
                logger.info(f"Gemini initialised via Vertex AI: project={project}, location={location}")
            except ImportError:
                logger.warning("vertexai package not installed")
            except Exception as e:
                logger.warning(f"Vertex AI init failed: {e}")
        else:
            logger.warning("Neither GEMINI_API_KEY nor GCP_PROJECT_ID set — AI features disabled")

    _initialized = True


def _get_model(system_instruction: str = None):
    """Return a GenerativeModel instance (google-generativeai or vertexai)."""
    _ensure_init()
    if not _vertex_available:
        raise RuntimeError(
            "Gemini not available. Set GEMINI_API_KEY (from aistudio.google.com/apikey) "
            "or GCP_PROJECT_ID for Vertex AI."
        )

    model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

    if _use_api_key:
        import google.generativeai as genai  # type: ignore
        from google.generativeai.types import GenerationConfig  # type: ignore
        return genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system_instruction,
        )
    else:
        from vertexai.generative_models import GenerativeModel  # type: ignore
        from prompts.gemini_prompt import SYSTEM_PROMPT
        return GenerativeModel(
            model_name=model_name,
            system_instruction=system_instruction or SYSTEM_PROMPT,
        )


# ── Public API ────────────────────────────────────────────────────────────────

def call_gemini(
    prompt: str,
    system: str = None,
    max_tokens: int = 2048,
    max_retries: int = 2,
) -> str:
    """
    Send a single (non-streaming) prompt to Gemini and return the text response.
    Works with both google-generativeai (API key mode) and vertexai.
    """
    from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable, GoogleAPIError

    model = _get_model(system)
    # Both SDKs accept a plain dict for generation_config
    generation_config = {"max_output_tokens": max_tokens, "temperature": 0.2}

    last_error: Exception | None = None
    for attempt in range(1, max_retries + 2):
        try:
            logger.info(f"call_gemini: attempt {attempt}")
            response = model.generate_content(prompt, generation_config=generation_config)
            text = response.text.strip()
            logger.info(f"call_gemini: success on attempt {attempt}, chars={len(text)}")
            return text

        except ResourceExhausted as exc:
            last_error = exc
            wait = 2 ** attempt
            logger.warning(f"Quota exceeded (attempt {attempt}). Retrying in {wait}s…")
            if attempt <= max_retries:
                time.sleep(wait)

        except ServiceUnavailable as exc:
            last_error = exc
            wait = 2 ** attempt
            logger.warning(f"Service unavailable (attempt {attempt}). Retrying in {wait}s…")
            if attempt <= max_retries:
                time.sleep(wait)

        except GoogleAPIError as exc:
            logger.error(f"Non-retryable Gemini error: {exc}")
            raise RuntimeError(f"Gemini API error: {exc}") from exc

        except Exception as exc:
            logger.error(f"Unexpected error calling Gemini: {exc}")
            raise RuntimeError(f"Unexpected Gemini error: {exc}") from exc

    raise RuntimeError(f"Gemini call failed after {max_retries + 1} attempts. Last error: {last_error}")


def stream_gemini(
    prompt: str,
    system: str = None,
    max_retries: int = 2,
) -> Generator[str, None, None]:
    """
    Send a prompt to Gemini and yield text chunks.
    Works with both google-generativeai (API key mode) and vertexai.
    """
    from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable, GoogleAPIError

    model = _get_model(system)
    generation_config = {"max_output_tokens": 4096, "temperature": 0.2}

    last_error: Exception | None = None
    for attempt in range(1, max_retries + 2):
        try:
            logger.info(f"stream_gemini: attempt {attempt}")
            response_stream = model.generate_content(
                prompt,
                generation_config=generation_config,
                stream=True,
            )
            for chunk in response_stream:
                if chunk.text:
                    yield chunk.text
            logger.info(f"stream_gemini: complete on attempt {attempt}")
            return

        except ResourceExhausted as exc:
            last_error = exc
            wait = 2 ** attempt
            logger.warning(f"Quota exceeded in stream (attempt {attempt}). Retrying in {wait}s…")
            if attempt <= max_retries:
                time.sleep(wait)

        except ServiceUnavailable as exc:
            last_error = exc
            wait = 2 ** attempt
            logger.warning(f"Service unavailable in stream (attempt {attempt}). Retrying in {wait}s…")
            if attempt <= max_retries:
                time.sleep(wait)

        except GoogleAPIError as exc:
            logger.error(f"Non-retryable Gemini stream error: {exc}")
            raise RuntimeError(f"Gemini API error: {exc}") from exc

        except Exception as exc:
            logger.error(f"Unexpected error in Gemini stream: {exc}")
            raise RuntimeError(f"Unexpected Gemini stream error: {exc}") from exc

    raise RuntimeError(f"Gemini streaming failed after {max_retries + 1} attempts. Last error: {last_error}")


def call_gemini_with_history(
    messages: list,
    system: str = None,
    max_tokens: int = 512,
) -> str:
    """
    Send a multi-turn conversation to Gemini (used for /ask Q&A endpoint).

    Args:
        messages:   List of dicts in Vertex AI format:
                    [{"role": "user", "parts": [{"text": "..."}]}, ...]
        system:     System instruction.
        max_tokens: Maximum output tokens (keep small for concise Q&A answers).

    Returns:
        The model's text response.
    """
    from vertexai.generative_models import GenerationConfig, Content, Part
    from google.api_core.exceptions import ResourceExhausted, GoogleAPIError

    _ensure_init()
    model = _get_model(system)
    generation_config = GenerationConfig(max_output_tokens=max_tokens, temperature=0.3)

    # Convert dict messages to Content objects expected by the SDK
    contents = []
    for msg in messages:
        role = msg["role"]
        parts = [Part.from_text(p["text"]) for p in msg["parts"]]
        contents.append(Content(role=role, parts=parts))

    try:
        response = model.generate_content(contents, generation_config=generation_config)
        return response.text.strip()
    except ResourceExhausted as exc:
        raise RuntimeError("Gemini quota exceeded. Please wait and try again.") from exc
    except GoogleAPIError as exc:
        raise RuntimeError(f"Vertex AI API error: {exc}") from exc
    except Exception as exc:
        raise RuntimeError(f"Unexpected error in Q&A call: {exc}") from exc


def parse_gemini_json(raw_text: str, prompt: str, max_retries: int = 1) -> dict:
    """
    Attempt to parse Gemini's response as JSON.
    If parsing fails, retry the call once with an explicit "return only JSON" suffix.

    Args:
        raw_text:   The raw string returned by Gemini.
        prompt:     The original prompt (used for the retry call).
        max_retries: How many retry attempts on parse failure (default 1).

    Returns:
        Parsed dict.

    Raises:
        ValueError: If JSON cannot be parsed after retries.
    """
    # Strip markdown fences if Gemini adds them despite instructions
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        cleaned = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as first_err:
        logger.warning(f"JSON parse failed on first attempt: {first_err}. Retrying…")

    if max_retries <= 0:
        raise ValueError(f"Gemini response is not valid JSON: {first_err}")

    # Retry with explicit JSON reminder
    retry_prompt = prompt + "\n\nIMPORTANT: Return ONLY raw JSON. No markdown, no explanation."
    try:
        retry_text = call_gemini(retry_prompt)
        retry_cleaned = retry_text.strip()
        if retry_cleaned.startswith("```"):
            lines = retry_cleaned.split("\n")
            retry_cleaned = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        return json.loads(retry_cleaned)
    except (json.JSONDecodeError, RuntimeError) as retry_err:
        raise ValueError(
            f"Gemini did not return valid JSON after retry. Error: {retry_err}\n"
            f"Raw response: {raw_text[:500]}"
        ) from retry_err
