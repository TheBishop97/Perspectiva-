"""
Pydantic schemas for request/response validation.
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, HttpUrl, Field

class SourceOut(BaseModel):
    id: int
    name: str
    base_url: str
    rss_url: HttpUrl
    created_at: datetime

    class Config:
        orm_mode = True

class ArticleOut(BaseModel):
    id: int
    source_id: int
    title: str
    url: HttpUrl
    published_at: Optional[datetime] = None
    full_text: Optional[str] = None
    summary: Optional[str] = None
    sentiment: Optional[str] = None
    created_at: datetime

    class Config:
        orm_mode = True
