# backend/common/redis_client.py
from typing import Optional, Dict
import redis.asyncio as aioredis
from backend.commons.configs  import get_settings, TOP_N_CACHED_WORDS
from sqlalchemy import update
from backend.commons.models import WordFrequency

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

async def get_word_frequency(redis_client: aioredis.Redis, word: str, db_session=None) -> Optional[int]:
    """
    Get word frequency from Redis cache with DB fallback.

    Args:
        redis_client: Redis client instance
        word: Word to look up
        db_session: Optional DB session for fallback lookup

    Returns:
        Word frequency or None if not found
    """
    try:
        key = f"word_freq:{word}"
        cached = await redis_client.get(key)
        if cached:
            if isinstance(cached, bytes):
                return int(cached.decode("utf-8"))
            return int(cached)
    except Exception:
        pass

    # Fallback to DB if not in cache and db_session is provided
    if db_session:
        try:
            from sqlalchemy import select
            from backend.commons.models import WordFrequency

            stmt = select(WordFrequency.frequency).where(WordFrequency.word == word)
            result = await db_session.execute(stmt)
            row = result.scalar_one_or_none()
            return row if row else None
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


async def reload_word_frequencies_from_db(db_session, top_n: int = TOP_N_CACHED_WORDS) -> None:
    """
    Reload top N word frequencies from PostgreSQL into Redis.
    Merges Redis cache with DB data, keeping only top N by frequency (DB is source of truth).
    Called on app startup to ensure Redis cache contains the most relevant words.

    Args:
        db_session: SQLAlchemy async session
        top_n: Number of top frequency words to keep in cache (default: 100)
    """
    try:
        from sqlalchemy import select
        from backend.commons.models import WordFrequency

        redis_client = get_redis_client()

        # Get current cache state
        current_cache = await get_all_word_frequencies(redis_client)

        # Fetch ALL word frequencies from DB (source of truth)
        stmt = select(WordFrequency.word, WordFrequency.frequency)
        result = await db_session.execute(stmt)
        rows = result.all()

        if rows:
            # DB is the source of truth - use DB frequencies
            all_word_freq = {row.word: row.frequency for row in rows}

            # Get top N words by frequency
            top_words = sorted(all_word_freq.items(), key=lambda x: x[1], reverse=True)[:top_n]
            top_word_dict = dict(top_words)

            # Remove words from cache that are not in top N
            words_to_remove = set(current_cache.keys()) - set(top_word_dict.keys())
            if words_to_remove:
                keys_to_delete = [f"word_freq:{word}" for word in words_to_remove]
                await redis_client.delete(*keys_to_delete)

            # Update cache with top N words
            await cache_word_frequencies(redis_client, top_word_dict)
            print(f"✓ Loaded top {len(top_word_dict)} word frequencies into Redis cache")
        else:
            print("✓ No word frequencies found in DB - cache is empty")

    except Exception as e:
        print(f"⚠ Failed to reload Redis from DB: {e}")
        # Don't fail startup if cache reload fails
