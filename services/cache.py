import logging
import os
import time
from typing import Optional, TYPE_CHECKING, Any

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv() -> bool:
        return False

# Type-only import (not executed at runtime)
if TYPE_CHECKING:
    from redis import Redis
    RedisType = Redis
else:
    RedisType = Any

try:
    import redis
    from redis.exceptions import RedisError
except ImportError:
    redis = None
    RedisError = Exception

load_dotenv()

logger = logging.getLogger(__name__)

_redis_client: Optional[RedisType] = None
_last_connect_attempt = 0.0
_RECONNECT_INTERVAL_SECONDS = 5.0


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)

    if value is None:
        return default

    try:
        return int(value)
    except ValueError:
        logger.warning(
            "Invalid integer for %s=%r. Using default=%s.",
            name,
            value,
            default,
        )
        return default


REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = _env_int("REDIS_PORT", 6379)
REDIS_DB = _env_int("REDIS_DB", 0)

CACHE_QUERY_TTL = _env_int("CACHE_QUERY_TTL", 1800)
CACHE_RETRIEVAL_TTL = _env_int("CACHE_RETRIEVAL_TTL", 3600)
CACHE_RESPONSE_TTL = _env_int("CACHE_RESPONSE_TTL", 86400)


def get_redis_client() -> Optional[RedisType]:
    global _redis_client, _last_connect_attempt

    if _redis_client is not None:
        return _redis_client

    now = time.monotonic()

    if now - _last_connect_attempt < _RECONNECT_INTERVAL_SECONDS:
        return None

    _last_connect_attempt = now

    if redis is None:
        logger.warning(
            "Redis package is not installed. Cache is disabled."
        )
        return None

    try:
        client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            socket_connect_timeout=0.2,
            socket_timeout=0.2,
            health_check_interval=30,
            decode_responses=True,
        )

        client.ping()

        logger.info(
            "Redis cache connected at %s:%s db=%s.",
            REDIS_HOST,
            REDIS_PORT,
            REDIS_DB,
        )

        _redis_client = client
        return client

    except RedisError as exc:
        logger.warning(
            "Redis cache unavailable. Continuing without cache. Error: %s",
            exc,
        )
        return None


def redis_status() -> str:
    global _redis_client

    client = get_redis_client()

    if client is None:
        return "unavailable"

    try:
        client.ping()
        return "available"

    except RedisError as exc:
        logger.warning(
            "Redis health check failed: %s",
            exc,
        )

        _redis_client = None
        return "unavailable"


def reset_redis_client() -> None:
    global _redis_client
    _redis_client = None