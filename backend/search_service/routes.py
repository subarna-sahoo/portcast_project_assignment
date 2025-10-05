from fastapi import APIRouter, Depends, HTTPException
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from backend.commons.schemas import SearchRequest, SearchResponse, ParagraphResponse
from backend.commons.database import get_db
from backend.search_service.service import SearchService

router = APIRouter(tags=["search"])

@router.post("/search", response_model=SearchResponse)
async def search_paragraphs(
    req: SearchRequest,
    db: AsyncSession = Depends(get_db),
):
    service = SearchService(db)
    try:
        paragraphs, total = await service.search_paragraphs(req.words, req.operator)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    resp_models = [
        ParagraphResponse.model_validate(p) for p in paragraphs
    ]

    return SearchResponse(paragraphs=resp_models, total=total)
