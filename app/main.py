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

@app.get("/sources/{source_id}", response_model=SourceOut)
def get_source(source_id: int, db: Session = Depends(get_db)):
    """Get a specific source by ID."""
    try:
        source = db.query(Source).filter(Source.id == source_id).first()
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        return source
    except SQLAlchemyError as e:
        logger.error("Error fetching source %d: %s", source_id, e)
        raise HTTPException(status_code=500, detail="Failed to fetch source")

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

@app.get("/articles/{article_id}", response_model=ArticleOut)
def get_article(article_id: int, db: Session = Depends(get_db)):
    """Get a specific article by ID."""
    try:
        article = (
            db.query(Article)
            .options(joinedload(Article.source))
            .filter(Article.id == article_id)
            .first()
        )
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        return article
    except SQLAlchemyError as e:
        logger.error("Error fetching article %d: %s", article_id, e)
        raise HTTPException(status_code=500, detail="Failed to fetch article")

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

        # Build article cards
        items = ""
        for a in articles:
            published = a.published_at.strftime("%Y-%m-%d %H:%M") if a.published_at else "Unknown date"
            summary = (a.summary or "")[:600]
            if len(a.summary or "") > 600:
                summary += "..."
                
            items += f'''
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
            '''

        # Build source options
        source_options = "<option value=''>All sources</option>"
        for source in sources:
            selected = "selected" if source_id == source.id else ""
            source_options += f"<option value='{source.id}' {selected}>{source.name}</option>"

        # Set selected values
        q_value = q or ""
        sentiment_selected = {
            "positive": "selected" if sentiment == "positive" else "",
            "neutral": "selected" if sentiment == "neutral" else "",
            "negative": "selected" if sentiment == "negative" else ""
        }

        html = f'''<!DOCTYPE html>
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
    .wrap {{ max-width: 1200px; margin: 0 auto; }}
    h1 {{ margin-bottom: .5rem; color: #9cd2ff; }}
    .subtitle {{ opacity: 0.8; margin-bottom: 2rem; }}
    .filters {{ 
      background: #131824; 
      padding: 1.5rem; 
      border-radius: 12px; 
      margin-bottom: 2rem;
      box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    }}
    .filters form {{ display: flex; gap: 1rem; flex-wrap: wrap; align-items: center; }}
    .card {{ 
      background: #131824; 
      padding: 1.5rem; 
      margin: 1rem 0; 
      border-radius: 12px; 
      box-shadow: 0 2px 8px rgba(0,0,0,.3);
      border-left: 4px solid #2b3a5d;
      transition: transform 0.2s ease;
    }}
    .card:hover {{ transform: translateY(-2px); }}
    .meta {{ 
      font-size: 0.85rem; 
      opacity: 0.8; 
      margin-bottom: 0.5rem; 
      display: flex;
      gap: 1rem;
      flex-wrap: wrap;
    }}
    .source {{ font-weight: 600; color: #9cd2ff; }}
    .date {{ color: #a0a8b8; }}
    .title a {{ 
      color: #e6e6e6; 
      text-decoration: none; 
      font-weight: 500;
      font-size: 1.1rem;
    }}
    .title a:hover {{ color: #9cd2ff; }}
    .summary {{ 
      opacity: 0.9; 
      margin-top: 0.75rem; 
      line-height: 1.5;
    }}
    .sent {{ 
      padding: 0.2rem 0.6rem; 
      border-radius: 8px; 
      font-size: 0.75rem; 
      font-weight: 600;
      text-transform: uppercase;
    }}
    .sent.positive {{ background: #1a4d3a; color: #4ade80; }}
    .sent.neutral {{ background: #374151; color: #d1d5db; }}
    .sent.negative {{ background: #7f1d1d; color: #f87171; }}
    input, select {{ 
      background: #0f1420; 
      color: #e6e6e6; 
      border: 1px solid #253047; 
      border-radius: 8px; 
      padding: 0.5rem 0.75rem;
      font-size: 0.9rem;
      min-width: 120px;
    }}
    input:focus, select:focus {{ outline: none; border-color: #9cd2ff; }}
    button {{ 
      background: #1a2440; 
      color: #e6e6e6; 
      border: 1px solid #2b3a5d; 
      border-radius: 8px; 
      padding: 0.5rem 1rem; 
      cursor: pointer;
      transition: background 0.2s ease;
    }}
    button:hover {{ background: #253047; }}
    @media (max-width: 768px) {{
      body {{ padding: 1rem; }}
      .filters form {{ flex-direction: column; align-items: stretch; }}
    }}
  </style>
</head>
<body>
  <div class='wrap'>
    <h1>📊 Perspectiva</h1>
    <p class='subtitle'>Real-time news aggregation with sentiment analysis</p>
    
    <div class='filters'>
      <form method='get' action='/'>
        <input type='text' name='q' placeholder='Search articles...' value='{q_value}' />
        <select name='sentiment'>
          <option value=''>All sentiments</option>
          <option value='positive' {sentiment_selected["positive"]}>Positive</option>
          <option value='neutral' {sentiment_selected["neutral"]}>Neutral</option>
          <option value='negative' {sentiment_selected["negative"]}>Negative</option>
        </select>
        <select name='source_id'>
          {source_options}
        </select>
        <button type='submit'>🔍 Filter</button>
        <a href='/' style='text-decoration: none;'>
          <button type='button'>🔄 Clear</button>
        </a>
      </form>
    </div>
    
    <div class='articles'>
      {items}
    </div>
    
    {'' if items else '<div class="card"><p>No articles found. The ingestion system may still be loading initial content.</p></div>'}
  </div>
  
  <script>
    // Auto-refresh every 5 minutes
    setTimeout(() => window.location.reload(), 300000);
  </script>
</body>
</html>'''
        return HTMLResponse(content=html)
        
    except SQLAlchemyError as e:
        logger.error("Error rendering home page: %s", e)
        return HTMLResponse(
            content="<h1>Database Error</h1><p>Unable to load articles.</p>",
            status_code=500
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
