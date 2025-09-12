"""
Database models: Source and Article.

- Source: one per RSS feed/site
- Article: stored articles, unique by url hash
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db import Base

class Source(Base):
    __tablename__ = "sources"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    base_url = Column(String(1024), nullable=False)
    rss_url = Column(String(2048), nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    articles = relationship("Article", back_populates="source", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Source(id={self.id} name={self.name} rss={self.rss_url})>"

class Article(Base):
    __tablename__ = "articles"
    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False, index=True)
    title = Column(String(1000), nullable=False)
    url = Column(String(2048), nullable=False)
    url_hash = Column(String(64), nullable=False, index=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    full_text = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    sentiment = Column(String(20), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    source = relationship("Source", back_populates="articles")

    __table_args__ = (
        UniqueConstraint("url_hash", name="uix_article_url_hash"),
        Index("ix_article_published_at", "published_at"),
    )

    def __repr__(self):
        return f"<Article(id={self.id} title={self.title[:30]!r})>"
