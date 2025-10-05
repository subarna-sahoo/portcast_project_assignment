from pydantic import BaseModel
from datetime import datetime
from typing import List, Literal, Optional



class ParagraphResponse(BaseModel):
    id: int
    content: str
    created_at: datetime

    class Config:
        from_attributes = True

