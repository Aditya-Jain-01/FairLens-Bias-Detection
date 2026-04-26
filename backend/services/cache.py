"""
services/cache.py
Phase 2.3 — Result caching for the bias analysis pipeline.

Strategy (two-tier):
  1. Redis (Cloud Memorystore) — when REDIS_URL env var is set.
     Shared across all Cloud Run instances, survives restarts, 1-hour TTL.
  2. cachetools LRU in-memory fallback — always available, zero infrastructure.
     Per-process only, resets on restart, max 128 entries.

Cache key: SHA-256 of (sorted CSV rows + sorted config JSON).
This ensures two identical uploads with identical configs always share a result.
"""

import hashlib
import json
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

_REDIS_URL = os.getenv("REDIS_URL", "")
_TTL       = int(os.getenv("CACHE_TTL_SECONDS", "3600"))   # 1 hour default

# ── In-memory fallback (always present) ───────────────────────────────────────
try:
    from cachetools import TTLCache
    _mem_cache: TTLCache = TTLCache(maxsize=128, ttl=_TTL)
except ImportError:
    _mem_cache = {}  # type: ignore[assignment]

# ── Redis client (lazy, optional) ─────────────────────────────────────────────
_redis = None


def _get_redis():
    global _redis
    if _redis is not None:
        return _redis
    if not _REDIS_URL:
        return None
    try:
        import redis as redis_lib
        _redis = redis_lib.from_url(_REDIS_URL, decode_responses=False)
        _redis.ping()
        logger.info("Redis cache connected.")
        return _redis
    except Exception as exc:
        logger.warning(f"Redis unavailable: {exc} — using in-memory cache only.")
        return None


# ── Public API ─────────────────────────────────────────────────────────────────

def compute_cache_key(job_id: str, config: dict) -> str:
    """
    Compute a deterministic cache key from the job's CSV content and configuration.

    We read the first 10,000 bytes of the CSV (enough to fingerprint the dataset
    without loading the whole file) and hash it together with the sorted config.
    """
    from services import storage

    fingerprint = b""
    try:
        csv_path = storage.get_local_file_path(job_id, "data.csv", bucket="uploads")
        with open(csv_path, "rb") as f:
            fingerprint = f.read(10_000)
    except Exception:
        # If the file isn't accessible, fall back to job_id only
        fingerprint = job_id.encode()

    config_bytes = json.dumps(config, sort_keys=True).encode()
    digest = hashlib.sha256(fingerprint + config_bytes).hexdigest()
    return digest


def get_cached_result(cache_key: str) -> Optional[dict]:
    """Return cached results dict, or None on cache miss."""
    # 1. Try Redis
    r = _get_redis()
    if r is not None:
        try:
            raw = r.get(f"fairlens:result:{cache_key}")
            if raw:
                logger.info(f"Cache HIT (Redis) for key {cache_key[:12]}…")
                return json.loads(raw)
        except Exception as exc:
            logger.warning(f"Redis get failed: {exc}")

    # 2. Try in-memory cache
    result = _mem_cache.get(cache_key)
    if result is not None:
        logger.info(f"Cache HIT (memory) for key {cache_key[:12]}…")
        return result

    logger.info(f"Cache MISS for key {cache_key[:12]}…")
    return None


def set_cached_result(cache_key: str, results: dict) -> None:
    """Store results in cache (Redis if available, always in memory)."""
    encoded = json.dumps(results).encode()

    # 1. Write to Redis
    r = _get_redis()
    if r is not None:
        try:
            r.setex(f"fairlens:result:{cache_key}", _TTL, encoded)
            logger.info(f"Cached result in Redis for key {cache_key[:12]}…")
        except Exception as exc:
            logger.warning(f"Redis set failed: {exc}")

    # 2. Always write to in-memory cache
    _mem_cache[cache_key] = results


def invalidate(cache_key: str) -> None:
    """Evict a specific entry (e.g. after re-analysis)."""
    _mem_cache.pop(cache_key, None)
    r = _get_redis()
    if r is not None:
        try:
            r.delete(f"fairlens:result:{cache_key}")
        except Exception:
            pass
