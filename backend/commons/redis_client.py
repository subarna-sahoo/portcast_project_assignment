# backend/common/redis_client.py
from typing import Optional, List, Tuple
import redis.asyncio as aioredis
import json
import asyncio
import httpx
from backend.commons.configs import (
    get_settings,
    TOP_N_CACHED_WORDS,
    REDIS_TOP_WORDS_KEY,
    REDIS_DEFINITION_PREFIX,
    REDIS_WORD_FREQ_TTL,
    REDIS_DEFINITION_TTL
)

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

async def cache_top_words(redis_client: aioredis.Redis, top_words: List[Tuple[str, int]]) -> None:
    """
    Cache top N word frequencies in Redis as a single JSON key.

    Args:
        redis_client: Redis client instance
        top_words: List of (word, frequency) tuples, sorted by frequency descending
    """
    if not top_words:
        return

    try:
        # Store as JSON: [["word1", 100], ["word2", 95], ...]
        cache_data = json.dumps(top_words)
        await redis_client.setex(REDIS_TOP_WORDS_KEY, REDIS_WORD_FREQ_TTL, cache_data)
    except Exception as e:
        print(f"⚠ Failed to cache top words: {e}")

async def get_top_words_from_cache(redis_client: aioredis.Redis) -> Optional[List[Tuple[str, int]]]:
    """
    Get top N words from Redis cache.

    Returns:
        List of (word, frequency) tuples or None if cache miss
    """
    try:
        cached = await redis_client.get(REDIS_TOP_WORDS_KEY)
        if cached:
            if isinstance(cached, bytes):
                cached = cached.decode("utf-8")
            data = json.loads(cached)
            # Convert back to list of tuples
            return [(item[0], item[1]) for item in data]
    except Exception as e:
        print(f"⚠ Failed to get top words from cache: {e}")
    return None

async def invalidate_top_words_cache(redis_client: aioredis.Redis) -> None:
    """
    Invalidate (delete) the top words cache.
    Called when word frequencies change (e.g., new paragraph ingested).
    """
    try:
        await redis_client.delete(REDIS_TOP_WORDS_KEY)
    except Exception as e:
        print(f"⚠ Failed to invalidate top words cache: {e}")

async def update_top_words_cache_from_db(redis_client: aioredis.Redis, db_session, top_n: int = TOP_N_CACHED_WORDS) -> None:
    """
    Fetch top N words from DB and update Redis cache.
    Called after word frequencies change.
    Also triggers async caching of definitions for these top words.

    Args:
        redis_client: Redis client instance
        db_session: DB session
        top_n: Number of top words to cache
    """
    try:
        from sqlalchemy import select
        from backend.commons.models import WordFrequency

        # Fetch top N from DB
        stmt = select(WordFrequency.word, WordFrequency.frequency).order_by(
            WordFrequency.frequency.desc()
        ).limit(top_n)
        result = await db_session.execute(stmt)
        rows = result.all()

        if rows:
            top_words = [(row.word, row.frequency) for row in rows]
            await cache_top_words(redis_client, top_words)

            # Trigger async caching of definitions in background (non-blocking)
            asyncio.create_task(cache_definitions_for_top_words_async(redis_client, top_words))
    except Exception as e:
        print(f"⚠ Failed to update top words cache: {e}")

async def cache_definitions_for_top_words_async(redis_client: aioredis.Redis, top_words: List[Tuple[str, int]]) -> None:
    """
    Asynchronously cache/refresh definitions for top words in Redis.
    - If definition exists in Redis: reset its TTL (extend expiry)
    - If definition doesn't exist: fetch from API and cache with TTL

    This runs in background and doesn't block the main flow.

    Args:
        redis_client: Redis client instance
        top_words: List of (word, frequency) tuples
    """
    if not top_words:
        return

    try:
        words_to_fetch = []

        # Check which definitions exist and reset TTL for existing ones
        for word, _ in top_words:
            key = f"{REDIS_DEFINITION_PREFIX}{word}"

            try:
                # Check if definition exists
                exists = await redis_client.exists(key)

                if exists:
                    # Reset TTL for existing definition
                    await redis_client.expire(key, REDIS_DEFINITION_TTL)
                    print(f"✓ Reset TTL for definition of '{word}'")
                else:
                    # Mark for fetching from API
                    words_to_fetch.append(word)
            except Exception as e:
                print(f"⚠ Failed to check/reset TTL for '{word}': {e}")
                words_to_fetch.append(word)  # Fetch as fallback

        # Fetch definitions for words not in cache
        if words_to_fetch:
            async with httpx.AsyncClient(timeout=10.0) as client:
                for word in words_to_fetch:
                    key = f"{REDIS_DEFINITION_PREFIX}{word}"

                    try:
                        resp = await client.get(f"{settings.dictionary_api_url}/{word}")
                        resp.raise_for_status()
                        data = resp.json()

                        # Extract definition
                        definition = (
                            data[0]["meanings"][0]["definitions"][0]["definition"]
                            if isinstance(data, list) and data and "meanings" in data[0]
                            else None
                        )

                        if definition:
                            # Cache with TTL
                            await redis_client.setex(key, REDIS_DEFINITION_TTL, definition)
                            print(f"✓ Cached new definition for '{word}'")
                    except Exception as e:
                        print(f"⚠ Failed to fetch/cache definition for '{word}': {e}")

    except Exception as e:
        print(f"⚠ Failed to cache definitions for top words: {e}")

async def reload_word_frequencies_from_db(db_session, top_n: int = TOP_N_CACHED_WORDS) -> None:
    """
    Reload top N word frequencies from PostgreSQL into Redis.
    Called on app startup to ensure Redis cache is populated.

    Args:
        db_session: SQLAlchemy async session
        top_n: Number of top frequency words to cache (default: 100)
    """
    try:
        redis_client = get_redis_client()
        await update_top_words_cache_from_db(redis_client, db_session, top_n)
        print(f"✓ Loaded top {top_n} word frequencies into Redis cache")
    except Exception as e:
        print(f"⚠ Failed to reload Redis from DB: {e}")
        # Don't fail startup if cache reload fails
