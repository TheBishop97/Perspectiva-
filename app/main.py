import logging
import threading
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, Depends, Query, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, desc, func
from sqlalchemy.exc import SQLAlchemyError

from app.db import Base, engine, SessionLocal
from app.models import Article, Source
from app.schemas import ArticleOut, SourceOut
from app.ingest import run_forever
from app.config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("perspectiva")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up Perspectiva...")
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified")
    
    # Start background ingestion thread
    ingestion_thread = threading.Thread(target=run_forever, daemon=True)
    ingestion_thread.start()
    logger.info("Started ingestion thread")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Perspectiva...")

app = FastAPI(
    title="Perspectiva", 
    version="1.0.0",
    description="A news aggregation and sentiment analysis platform",
    lifespan=lifespan
)

def get_db():
    """Database dependency."""
    db = SessionLocal()
    try:
        yield db
    except SQLAlchemyError as e:
        db.rollback()
        logger.error("Database error: %s", e)
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        db.close()

@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "perspectiva", "version": "1.0.0"}

@app.get("/sources", response_model=List[SourceOut])
def list_sources(db: Session = Depends(get_db)):
    """List all news sources."""
    try:
        sources = db.query(Source).order_by(Source.name).all()
        return sources
    except SQLAlchemyError as e:
        logger.error("Error fetching sources: %s", e)
        raise HTTPException(status_code=500, detail="Failed to fetch sources")

@app.get("/articles", response_model=List[ArticleOut])
def list_articles(
    db: Session = Depends(get_db),
    q: Optional[str] = Query(None, description="Search keyword in title"),
    limit: int = Query(20, ge=1, le=100, description="Number of articles to return"),
    offset: int = Query(0, ge=0, description="Number of articles to skip"),
    sentiment: Optional[str] = Query(None, regex="^(positive|neutral|negative)$"),
    source_id: Optional[int] = Query(None),
):
    """List articles with optional filtering."""
    try:
        stmt = (
            select(Article)
            .options(joinedload(Article.source))
            .order_by(desc(Article.published_at), desc(Article.id))
        )
        
        if q:
            stmt = stmt.filter(Article.title.ilike(f"%{q}%"))
        if sentiment:
            stmt = stmt.filter(Article.sentiment == sentiment)
        if source_id:
            stmt = stmt.filter(Article.source_id == source_id)
        
        stmt = stmt.offset(offset).limit(limit)
        articles = db.execute(stmt).scalars().all()
        return articles
        
    except SQLAlchemyError as e:
        logger.error("Error fetching articles: %s", e)
        raise HTTPException(status_code=500, detail="Failed to fetch articles")

@app.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """Get platform statistics."""
    try:
        total_articles = db.query(func.count(Article.id)).scalar()
        total_sources = db.query(func.count(Source.id)).scalar()
        
        sentiment_stats = (
            db.query(Article.sentiment, func.count(Article.id))
            .group_by(Article.sentiment)
            .all()
        )
        
        return {
            "total_articles": total_articles,
            "total_sources": total_sources,
            "sentiment_breakdown": dict(sentiment_stats)
        }
    except SQLAlchemyError as e:
        logger.error("Error fetching stats: %s", e)
        raise HTTPException(status_code=500, detail="Failed to fetch statistics")

@app.get("/", response_class=HTMLResponse)
def home(
    db: Session = Depends(get_db), 
    q: Optional[str] = Query(None),
    sentiment: Optional[str] = Query(None),
    source_id: Optional[int] = Query(None)
):
    """Serve the main HTML interface."""
    try:
        stmt = (
            select(Article)
            .options(joinedload(Article.source))
            .order_by(desc(Article.published_at), desc(Article.id))
            .limit(50)
        )
        
        if q:
            stmt = stmt.filter(Article.title.ilike(f"%{q}%"))
        if sentiment:
            stmt = stmt.filter(Article.sentiment == sentiment)
        if source_id:
            stmt = stmt.filter(Article.source_id == source_id)
        
        articles = db.execute(stmt).scalars().all()
        sources = db.query(Source).order_by(Source.name).all()

        # Build HTML response with modern interface
        items = ""
        for a in articles:
            published = a.published_at.strftime("%Y-%m-%d %H:%M") if a.published_at else "Unknown date"
            summary = (a.summary or "")[:600]
            if len(a.summary or "") > 600:
                summary += "..."
                
            items += f"""
            <div class='card'>
              <div class='meta'>
                <span class='source'>[{a.source.name}]</span>
                <span class='date'>{published}</span>
                <span class='sent {a.sentiment or ""}'>{(a.sentiment or "").title()}</span>
              </div>
              <div class='title'>
                <a href='{a.url}' target='_blank' rel='noopener noreferrer'>{a.title}</a>
              </div>
              <div class='summary'>{summary}</div>
            </div>
            """

        source_options = "<option value=''>All sources</option>"
        for source in sources:
            selected = "selected" if source_id == source.id else ""
            source_options += f"<option value='{source.id}' {selected}>{source.name}</option>"

        q_value = q or ""
        sentiment_selected = {
            "positive": "selected" if sentiment == "positive" else "",
            "neutral": "selected" if sentiment == "neutral" else "",
            "negative": "selected" if sentiment == "negative" else ""
        }

        html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
          <meta charset='utf-8'/>
          <meta name="viewport" content="width=device-width, initial-scale=1"/>
          <title>Perspectiva — News Analytics</title>
          <style>
            * {{ box-sizing: border-box; }}
            body {{ 
              font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
              margin: 0; padding: 2rem; 
              background: #0b0e14; 
              color: #e6e6e6; 
              line-height: 1.6;
            }}
