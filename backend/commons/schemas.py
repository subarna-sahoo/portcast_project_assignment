from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import List, Literal, Optional



class ParagraphResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    content: str
    created_at: datetime

class SearchRequest(BaseModel):
    words: List[str]
    operator: Literal["and", "or"]

class SearchResponse(BaseModel):
    paragraphs: List[ParagraphResponse]
    total: int

class WordDefinition(BaseModel):
    word: str
    definition: str
    frequency: int

class DictionaryResponse(BaseModel):
    definitions: List[WordDefinition]
