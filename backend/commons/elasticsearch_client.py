from elasticsearch import AsyncElasticsearch
from typing import Any, Dict, List, Optional
from backend.commons.configs import get_settings

settings = get_settings()


class ElasticsearchClient:
    _client: Optional[AsyncElasticsearch] = None

    @classmethod
    def get_client(cls) -> AsyncElasticsearch:
        if cls._client is None:
            cls._client = AsyncElasticsearch([settings.elasticsearch_url])
        return cls._client

    @classmethod
    async def close_client(cls):
        if cls._client:
            await cls._client.close()
            cls._client = None

    @classmethod
    async def index_document(cls, index: str, id: Any, document: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
        client = cls.get_client()
        resp = await client.index(index=index, id=id, document=document, **kwargs)
        return resp
    
    @classmethod
    async def search(cls, index: str, query: Dict[str, Any], size: int = 10, **kwargs: Any) -> Dict[str, Any]:
        client = cls.get_client()
        resp = await client.search(index=index, query=query, size=size, **kwargs)
        return resp
