# backend/common/redis_client.py
from typing import Optional, Dict
import redis.asyncio as aioredis
from backend.commons.configs  import get_settings

settings = get_settings()

_redis_client: Optional[aioredis.Redis] = None

def get_redis_client() -> aioredis.Redis:
    """
    Return a shared Redis client (connection pool). Creates it on first call.
    Use this as a FastAPI dependency: Depends(get_redis_client)
    """
    global _redis_client
    if _redis_client is None:
        # create a ConnectionPool so connections are reused and limited
        pool = aioredis.ConnectionPool.from_url(
            settings.redis_url,
            max_connections=50,  # tune for your environment
            decode_responses=False,  # we store bytes; decode when needed
        )
        _redis_client = aioredis.Redis(connection_pool=pool)
    return _redis_client

async def close_redis_client() -> None:
    """Call this on app shutdown to cleanly close the client."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None

async def cache_word_frequencies(redis_client: aioredis.Redis, word_frequencies: Dict[str, int]) -> None:
    """
    Batch cache word frequencies in Redis with TTL of 7 days.
    Uses pipeline for efficiency.
    """
    if not word_frequencies:
        return

    pipe = redis_client.pipeline()
    ttl = 7 * 24 * 60 * 60  # 7 days in seconds

    for word, count in word_frequencies.items():
        key = f"word_freq:{word}"
        pipe.setex(key, ttl, str(count))

    await pipe.execute()

async def get_word_frequency(redis_client: aioredis.Redis, word: str) -> Optional[int]:
    """Get word frequency from Redis cache."""
    try:
        key = f"word_freq:{word}"
        cached = await redis_client.get(key)
        if cached:
            if isinstance(cached, bytes):
                return int(cached.decode("utf-8"))
            return int(cached)
    except Exception:
        pass
    return None

async def get_all_word_frequencies(redis_client: aioredis.Redis) -> Dict[str, int]:
    """
    Get all cached word frequencies from Redis.
    Returns dict of {word: frequency}
    """
    try:
        keys = await redis_client.keys("word_freq:*")
        if not keys:
            return {}

        pipe = redis_client.pipeline()
        for key in keys:
            pipe.get(key)

        values = await pipe.execute()

        result = {}
        for key, value in zip(keys, values):
            if value:
                # Extract word from key (word_freq:word -> word)
                word_key = key.decode("utf-8") if isinstance(key, bytes) else key
                word = word_key.split(":", 1)[1]
                freq = int(value.decode("utf-8") if isinstance(value, bytes) else value)
                result[word] = freq

        return result
    except Exception:
        return {}

async def reload_word_frequencies_from_db(db_session) -> None:
    """
    Reload word frequencies from PostgreSQL into Redis.
    Called on app startup to ensure Redis cache is populated.

    Args:
        db_session: SQLAlchemy async session
    """
    try:
        from sqlalchemy import select
        from backend.commons.models import WordFrequency

        redis_client = get_redis_client()

        # Fetch all word frequencies from DB
        stmt = select(WordFrequency.word, WordFrequency.frequency)
        result = await db_session.execute(stmt)
        rows = result.all()

        if rows:
            word_freq_dict = {row.word: row.frequency for row in rows}
            # Batch cache in Redis
            await cache_word_frequencies(redis_client, word_freq_dict)
            print(f"✓ Loaded {len(word_freq_dict)} word frequencies into Redis cache")
        else:
            print("✓ No word frequencies found in DB - cache is empty")

    except Exception as e:
        print(f"⚠ Failed to reload Redis from DB: {e}")
        # Don't fail startup if cache reload fails
