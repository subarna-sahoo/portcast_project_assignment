# backend/ingest_service/routes.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from backend.commons.database import get_db
from backend.commons.redis_client import get_redis_client
from backend.ingest_service.service import IngestService
from backend.commons.schemas import ParagraphResponse

router = APIRouter()

@router.post("/fetch", response_model=ParagraphResponse)
async def fetch_paragraph(
    db: AsyncSession = Depends(get_db),
    redis_client = Depends(get_redis_client)
):
    """Fetch a paragraph from metaphorpsum and store it"""
    try:
        service = IngestService(db, redis_client)
        paragraph = await service.fetch_and_store_paragraph()
        return ParagraphResponse.model_validate(paragraph)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
