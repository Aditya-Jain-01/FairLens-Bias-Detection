"""
FairLens — Vertex AI Client Wrapper

Provides call_gemini() and stream_gemini() with retry logic.
Lazily initialises Vertex AI — the app starts cleanly in local mode
even when GCP_PROJECT_ID is not set.
"""

import os
import time
import json
import logging
from typing import Generator

logger = logging.getLogger(__name__)

# ── Initialisation ────────────────────────────────────────────────────────────

_initialized = False
_vertex_available = False


def _ensure_init() -> None:
    """Lazily initialise Vertex AI once per process. Non-fatal if GCP is unavailable."""
    global _initialized, _vertex_available
    if not _initialized:
        project = os.getenv("GCP_PROJECT_ID")
        location = os.getenv("VERTEX_AI_LOCATION", "us-central1")
        if project:
            try:
                import vertexai
                vertexai.init(project=project, location=location)
                _vertex_available = True
                logger.info(f"Vertex AI initialised: project={project}, location={location}")
            except ImportError:
                logger.warning("vertexai package not installed — AI features disabled")
            except Exception as e:
                logger.warning(f"Vertex AI init failed: {e} — AI features disabled")
        else:
            logger.warning(
                "GCP_PROJECT_ID not set — Vertex AI calls will fail at runtime. "
                "Mock pipeline will still work for frontend testing."
            )
        _initialized = True


def _get_model(system_instruction: str = None):
    """Return a GenerativeModel instance."""
    _ensure_init()
    if not _vertex_available:
        raise RuntimeError(
            "Vertex AI not available. Set GCP_PROJECT_ID in .env and install "
            "google-cloud-aiplatform to enable AI features."
        )

    from vertexai.generative_models import GenerativeModel
    from prompts.gemini_prompt import SYSTEM_PROMPT

    if system_instruction is None:
        system_instruction = SYSTEM_PROMPT

    model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-pro")
    return GenerativeModel(
        model_name=model_name,
        system_instruction=system_instruction,
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

    Args:
        prompt:      The user-turn prompt text.
        system:      System instruction (defaults to SYSTEM_PROMPT).
        max_tokens:  Maximum number of output tokens.
        max_retries: Number of retry attempts on transient errors.

    Returns:
        The model's text response as a plain string.

    Raises:
        RuntimeError: On non-retryable errors or exhausted retries.
    """
    from vertexai.generative_models import GenerationConfig
    from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable, GoogleAPIError

    model = _get_model(system)
    generation_config = GenerationConfig(max_output_tokens=max_tokens, temperature=0.2)

    last_error: Exception | None = None
    for attempt in range(1, max_retries + 2):  # attempts: 1, 2, 3
        try:
            logger.info(f"call_gemini: attempt {attempt}")
            response = model.generate_content(
                prompt,
                generation_config=generation_config,
            )
            text = response.text.strip()
            logger.info(f"call_gemini: success on attempt {attempt}, chars={len(text)}")
            return text

        except ResourceExhausted as exc:
            last_error = exc
            wait = 2 ** attempt
            logger.warning(f"Quota exceeded (attempt {attempt}). Retrying in {wait}s… {exc}")
            if attempt <= max_retries:
                time.sleep(wait)

        except ServiceUnavailable as exc:
            last_error = exc
            wait = 2 ** attempt
            logger.warning(f"Vertex AI unavailable (attempt {attempt}). Retrying in {wait}s… {exc}")
            if attempt <= max_retries:
                time.sleep(wait)

        except GoogleAPIError as exc:
            logger.error(f"Non-retryable Vertex AI error: {exc}")
            raise RuntimeError(f"Vertex AI API error: {exc}") from exc

        except Exception as exc:
            logger.error(f"Unexpected error calling Gemini: {exc}")
            raise RuntimeError(f"Unexpected Gemini error: {exc}") from exc

    raise RuntimeError(
        f"Gemini call failed after {max_retries + 1} attempts. "
        f"Last error: {last_error}"
    )


def stream_gemini(
    prompt: str,
    system: str = None,
    max_retries: int = 2,
) -> Generator[str, None, None]:
    """
    Send a prompt to Gemini and yield text chunks as they arrive (streaming).

    Args:
        prompt:      The user-turn prompt text.
        system:      System instruction (defaults to SYSTEM_PROMPT).
        max_retries: Number of retry attempts on transient errors.

    Yields:
        Text chunks (strings) from the model as they stream.

    Raises:
        RuntimeError: On non-retryable errors or exhausted retries.
    """
    from vertexai.generative_models import GenerationConfig
    from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable, GoogleAPIError

    model = _get_model(system)
    generation_config = GenerationConfig(max_output_tokens=4096, temperature=0.2)

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
            logger.info(f"stream_gemini: stream complete on attempt {attempt}")
            return  # success — exit generator

        except ResourceExhausted as exc:
            last_error = exc
            wait = 2 ** attempt
            logger.warning(f"Quota exceeded in stream (attempt {attempt}). Retrying in {wait}s…")
            if attempt <= max_retries:
                time.sleep(wait)

        except ServiceUnavailable as exc:
            last_error = exc
            wait = 2 ** attempt
            logger.warning(f"Vertex AI unavailable in stream (attempt {attempt}). Retrying in {wait}s…")
            if attempt <= max_retries:
                time.sleep(wait)

        except GoogleAPIError as exc:
            logger.error(f"Non-retryable Vertex AI stream error: {exc}")
            raise RuntimeError(f"Vertex AI API error: {exc}") from exc

        except Exception as exc:
            logger.error(f"Unexpected error in Gemini stream: {exc}")
            raise RuntimeError(f"Unexpected Gemini stream error: {exc}") from exc

    raise RuntimeError(
        f"Gemini streaming failed after {max_retries + 1} attempts. "
        f"Last error: {last_error}"
    )


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
