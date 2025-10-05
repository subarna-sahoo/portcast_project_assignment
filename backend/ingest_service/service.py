import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from backend.commons.models import Paragraph
from backend.commons.configs import get_settings
from elasticsearch import AsyncElasticsearch

settings = get_settings()


class IngestService:
    def __init__(self, db: AsyncSession):
        self.db = db
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
        es = AsyncElasticsearch([self.settings.elasticsearch_url])
        try:
            await es.index(
                index="paragraphs",
                id=paragraph.id,
                document={
                    "id": paragraph.id,
                    "content": paragraph.content,
                    "created_at": paragraph.created_at.isoformat(),
                },
            )
        finally:
            await es.close()

        return paragraph
