from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, HttpUrl

class SourceOut(BaseModel):
    id: int
    name: str
    base_url: str
    rss_url: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}

class SourceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    base_url: HttpUrl
    rss_url: Optional[HttpUrl] = None

class ArticleOut(BaseModel):
    id: int
    source: SourceOut
    title: str
    url: str
    published_at: Optional[datetime] = None
    summary: Optional[str] = None
    sentiment: Optional[str] = Field(None, pattern="^(positive|neutral|negative)$")
    created_at: datetime

    model_config = {"from_attributes": True}

class ArticleCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=800)
    url: HttpUrl
    published_at: Optional[datetime] = None
    full_text: Optional[str] = None
    summary: Optional[str] = None
    sentiment: Optional[str] = Field(None, pattern="^(positive|neutral|negative)$")
