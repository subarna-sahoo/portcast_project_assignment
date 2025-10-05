# backend/dict_service/service.py
from typing import List

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.commons.models import WordFrequency
from backend.commons.configs import get_settings, REDIS_DEFINITION_PREFIX, REDIS_DEFINITION_TTL
from backend.commons.schemas import WordDefinition
from backend.commons.redis_client import get_top_words_from_cache

settings = get_settings()


class DictionaryService:
    def __init__(self, db: AsyncSession, redis_client):
        self.db = db
        self.redis = redis_client
        self.settings = settings

    async def get_top_words_definitions(self, top_n: int = 10) -> List[WordDefinition]:
        """
        1) Try to get top N words from Redis cache (fast path)
        2) If cache miss, query DB and cache the result
        3) For each word: check definition cache in Redis
        4) If definition not cached, call Dictionary API and cache it
        Returns list of WordDefinition Pydantic models
        """
        # Try to get word frequencies from Redis cache first
        top_words_cached = await get_top_words_from_cache(self.redis)

        if top_words_cached and len(top_words_cached) >= top_n:
            # Use cached data, take top N
            top_words = top_words_cached[:top_n]
        else:
            # Cache miss - fall back to DB
            stmt = select(WordFrequency.word, WordFrequency.frequency).order_by(
                WordFrequency.frequency.desc()
            ).limit(top_n)
            result = await self.db.execute(stmt)
            rows = result.all()
            top_words = [(row.word, row.frequency) for row in rows]

        if not top_words:
            return []  # No words in database or cache

        results: List[WordDefinition] = []

        # Fetch definitions for each word
        async with httpx.AsyncClient(timeout=10.0) as client:
            for word, count in top_words:
                key = f"{REDIS_DEFINITION_PREFIX}{word}"
                definition = None

                # Try to get definition from Redis cache
                try:
                    cached = await self.redis.get(key)
                    if cached:
                        # cached is bytes if decode_responses=False
                        if isinstance(cached, bytes):
                            definition = cached.decode("utf-8", errors="ignore")
                        else:
                            definition = str(cached)
                except Exception:
                    # Redis transient issue — fall back to API
                    pass

                # If not cached, call Dictionary API
                if not definition:
                    try:
                        resp = await client.get(f"{self.settings.dictionary_api_url}/{word}")
                        resp.raise_for_status()
                        data = resp.json()
                        # defensive extraction (API structure may vary)
                        definition = (
                            data[0]["meanings"][0]["definitions"][0]["definition"]
                            if isinstance(data, list) and data and "meanings" in data[0]
                            else None
                        )
                        if definition:
                            # Cache definition with TTL from constants
                            try:
                                await self.redis.setex(key, REDIS_DEFINITION_TTL, definition)
                            except Exception:
                                # caching is best-effort; ignore failures
                                pass
                    except Exception as e:
                        print(f"⚠ Failed to fetch definition for '{word}': {e}")
                        definition = None

                if not definition:
                    definition = "Definition not found"

                results.append(WordDefinition(word=word, definition=definition, frequency=count))

        return results
