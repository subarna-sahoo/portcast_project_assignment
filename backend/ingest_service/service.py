import re
from collections import Counter
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from backend.commons.models import Paragraph, WordFrequency
from backend.commons.configs import get_settings
from backend.commons.elasticsearch_client import ElasticsearchClient
from backend.commons.redis_client import cache_word_frequencies


settings = get_settings()

# lightweight stop-words set; extend as needed
_STOP_WORDS = {
    "the","and","for","with","from","that","this","those","these","have",
    "will","could","should","there","which","what","when","then","than",
    "were","been","been","being","have","has","had","you","your","are","was",
    "not","but","also","their","they","them","its","it","use","used"
}


class IngestService:
    def __init__(self, db: AsyncSession, redis_client=None):
        self.db = db
        self.redis = redis_client
        self.settings = settings

    async def fetch_and_store_paragraph(self) -> Paragraph:
        """Fetch paragraph from metaphorpsum and store in DB and Elasticsearch"""
        async with httpx.AsyncClient() as client:
            response = await client.get(self.settings.metaphorpsum_url)
            response.raise_for_status()
            content = response.text

        # Store in PostgreSQL
        paragraph = Paragraph(content=content)
        self.db.add(paragraph)
        await self.db.commit()
        await self.db.refresh(paragraph)

        # Index in Elasticsearch
        await ElasticsearchClient.index_document(
                    index="paragraphs",
                    id=paragraph.id,
                    document={
                        "id": paragraph.id,
                        "content": paragraph.content,
                        "created_at": paragraph.created_at.isoformat(),
                    },
                )

        # Extract and update word frequencies in background
        await self._update_word_frequencies(content)

        return paragraph

    async def _update_word_frequencies(self, new_content: str) -> None:
        """
        Extract words from new content, update frequency counts in DB and Redis.
        This runs as part of ingestion to keep frequencies up-to-date.
        """
        # Extract words from new content
        words = re.findall(r"\b[a-zA-Z]{4,}\b", new_content.lower())
        words = [w for w in words if w not in _STOP_WORDS]
        new_word_counts = Counter(words)

        if not new_word_counts:
            return

        # Upsert word frequencies in DB (PostgreSQL)
        for word, count in new_word_counts.items():
            stmt = insert(WordFrequency).values(
                word=word,
                frequency=count
            ).on_conflict_do_update(
                index_elements=['word'],
                set_=dict(frequency=WordFrequency.frequency + count)
            )
            await self.db.execute(stmt)

        await self.db.commit()

        # Update Redis cache with new frequencies
        if self.redis:
            # Fetch updated frequencies from DB
            stmt = select(WordFrequency.word, WordFrequency.frequency).where(
                WordFrequency.word.in_(list(new_word_counts.keys()))
            )
            result = await self.db.execute(stmt)
            updated_frequencies = {row.word: row.frequency for row in result}

            # Cache in Redis
            try:
                await cache_word_frequencies(self.redis, updated_frequencies)
            except Exception:
                # Best effort caching, ignore failures
                pass
