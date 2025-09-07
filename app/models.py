from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from sqlalchemy.types import JSON as JSONType
from app.db import Base

class Source(Base):
    __tablename__ = "sources"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False, index=True)
    base_url = Column(String(300), nullable=False, unique=True)
    rss_url = Column(String(500), nullable=True, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    articles = relationship("Article", back_populates="source", cascade="all, delete-orphan")

class Article(Base):
    __tablename__ = "articles"
    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("sources.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(800), nullable=False)
    url = Column(String(1000), nullable=False)
    url_hash = Column(String(64), nullable=False, unique=True, index=True)
    published_at = Column(DateTime, nullable=True, index=True)
    full_text = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    sentiment = Column(String(16), nullable=True, index=True)  # positive | neutral | negative
    meta = Column(JSONType, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    source = relationship("Source", back_populates="articles")

    __table_args__ = (
        UniqueConstraint("url_hash", name="uq_articles_url_hash"),
        Index("ix_articles_published_sentiment", "published_at", "sentiment"),
        Index("ix_articles_source_published", "source_id", "published_at"),
    )
