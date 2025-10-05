from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from backend.commons.database import get_db
from backend.commons.schemas import DictionaryResponse, WordDefinition
from backend.dict_service.service import DictionaryService

# Optional: dependencies for redis and HTTP client, if you're injecting them
from backend.commons.redis_client import get_redis_client


router = APIRouter(tags=["dictionary"])


@router.get("/dictionary", response_model=DictionaryResponse)
async def get_dictionary(
    db: AsyncSession = Depends(get_db),
    redis_client = Depends(get_redis_client),
) -> DictionaryResponse:
    service = DictionaryService(db, redis_client)
    try:
        definitions: List[WordDefinition] = await service.get_top_words_definitions()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return DictionaryResponse(definitions=definitions)
