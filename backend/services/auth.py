"""
services/auth.py
================
API Key authentication dependency for FairLens.

Usage in any router:
    from services.auth import require_api_key
    @router.post("/my-route", dependencies=[Depends(require_api_key)])

The client must send the header:
    X-API-Key: <value of SECRET_API_KEY env var>

Public endpoints (health, root, docs) do NOT use this dependency.

Env var:
    SECRET_API_KEY — set in .env for local dev, Cloud Secret Manager for production.
                     If not set, the server starts but logs a loud warning — every
                     request will be rejected until the key is configured.
"""

import os
import hmac
import logging
from typing import Optional

from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader

logger = logging.getLogger(__name__)

# Header name clients must send
_API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


def _get_configured_key() -> Optional[str]:
    """Read the expected API key from env. Warn loudly if missing."""
    key = os.getenv("SECRET_API_KEY", "").strip()
    if not key:
        logger.warning(
            "SECRET_API_KEY is not set! All authenticated endpoints will return 403. "
            "Set SECRET_API_KEY in your .env file or Cloud Run configuration."
        )
        return None
    return key


async def require_api_key(api_key: Optional[str] = Security(_API_KEY_HEADER)) -> str:
    """
    FastAPI dependency. Raises 403 if the X-API-Key header is missing or wrong.
    Use via:  dependencies=[Depends(require_api_key)]
    Or as an injected parameter:  api_key: str = Depends(require_api_key)
    """
    configured_key = _get_configured_key()

    if configured_key is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Server is not configured (SECRET_API_KEY missing). Contact the administrator.",
        )

    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing X-API-Key header.",
        )

    # Use constant-time comparison to prevent timing attacks
    if not hmac.compare_digest(api_key.encode(), configured_key.encode()):
        logger.warning("Rejected request with invalid API key.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key.",
        )

    return api_key
