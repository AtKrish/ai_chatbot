import json
import logging
import threading
from typing import Any, Dict, Optional

from services.cache import RedisError, get_redis_client, redis_status, reset_redis_client


logger = logging.getLogger(__name__)

_stats_lock = threading.Lock()
_hit_count = 0
_miss_count = 0


def _record_hit() -> None:
    global _hit_count
    with _stats_lock:
        _hit_count += 1


def _record_miss() -> None:
    global _miss_count
    with _stats_lock:
        _miss_count += 1


def get(key: str) -> Optional[Any]:
    client = get_redis_client()
    if client is None:
        logger.info("CACHE MISS redis_unavailable key=%s", key)
        _record_miss()
        return None

    try:
        raw_value = client.get(key)
        if raw_value is None:
            logger.info("CACHE MISS key=%s", key)
            _record_miss()
            return None

        logger.info("CACHE HIT key=%s", key)
        _record_hit()
        return json.loads(raw_value)
    except (RedisError, json.JSONDecodeError, TypeError) as exc:
        logger.warning("CACHE MISS cache_read_failed key=%s error=%s", key, exc)
        if isinstance(exc, RedisError):
            reset_redis_client()
        _record_miss()
        return None


def set(key: str, value: Any, ttl: int) -> bool:
    client = get_redis_client()
    if client is None:
        return False

    try:
        client.setex(key, ttl, json.dumps(value, ensure_ascii=True))
        logger.info("CACHE STORE key=%s ttl=%s", key, ttl)
        return True
    except (RedisError, TypeError, ValueError) as exc:
        logger.warning("CACHE STORE failed key=%s error=%s", key, exc)
        if isinstance(exc, RedisError):
            reset_redis_client()
        return False


def delete(key: str) -> bool:
    client = get_redis_client()
    if client is None:
        return False

    try:
        client.delete(key)
        return True
    except RedisError as exc:
        logger.warning("CACHE DELETE failed key=%s error=%s", key, exc)
        reset_redis_client()
        return False


def exists(key: str) -> bool:
    client = get_redis_client()
    if client is None:
        return False

    try:
        return bool(client.exists(key))
    except RedisError as exc:
        logger.warning("CACHE EXISTS failed key=%s error=%s", key, exc)
        reset_redis_client()
        return False


def stats() -> Dict[str, Any]:
    with _stats_lock:
        total = _hit_count + _miss_count
        hit_ratio = round(_hit_count / total, 4) if total else 0.0

        return {
            "hit_count": _hit_count,
            "miss_count": _miss_count,
            "hit_ratio": hit_ratio,
            "redis_status": redis_status(),
        }
