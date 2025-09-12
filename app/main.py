"""
FastAPI application entrypoint.

Exposes endpoints:
 - GET /articles : list articles
 - GET /articles/{id} : get article by id
 - GET /sources : list sources
 - GET /health : simple health check

On startup the DB is created (if missing) and the ingest background thread is started.
"""

import logging
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from app.db import init_db, get_db
from app.ingest import run_forever, run_once
from app.schemas import ArticleOut, SourceOut
from app.models import Article, Source
from app.config import settings

logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL, "INFO"))
logger = logging.getLogger("app.main")

app = FastAPI(title="Perspectiva", version="0.1.0")

@app.on_event("startup")
def startup_event():
    # initialize database and start background ingestion thread
    init_db()
    run_forever(start_immediately=True)
    logger.info("Application startup complete. Ingest loop started (interval=%s seconds).", settings.FETCH_INTERVAL_SECONDS)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/sources", response_model=List[SourceOut])
def list_sources(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    return db.query(Source).offset(skip).limit(limit).all()

@app.get("/articles", response_model=List[ArticleOut])
def list_articles(skip: int = 0, limit: int = Query(50, le=200), db: Session = Depends(get_db)):
    return db.query(Article).order_by(Article.published_at.desc().nullslast(), Article.created_at.desc()).offset(skip).limit(limit).all()

@app.get("/articles/{article_id}", response_model=ArticleOut)
def get_article(article_id: int, db: Session = Depends(get_db)):
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article

@app.post("/ingest/run-once")
def endpoint_run_once(db: Session = Depends(get_db)):
    """
    Trigger a single ingestion run (useful for manual runs in dev/test).
    """
    run_once(db)
    return {"status": "ok"}

@app.get("/", response_class=HTMLResponse)
def home(db: Session = Depends(get_db)):
    """
    Simple homepage that shows recent articles in a minimal HTML table.
    """
    articles = db.query(Article).order_by(Article.created_at.desc()).limit(30).all()
    html = ["<html><head><title>Perspectiva</title></head><body>"]
    html.append("<h1>Recent Articles</h1>")
    html.append("<table border='1' cellpadding='6'><tr><th>Title</th><th>Source</th><th>Published</th><th>Sentiment</th></tr>")
    for a in articles:
        source_name = a.source.name if a.source else "unknown"
        published = a.published_at.isoformat() if a.published_at else ""
        html.append(f"<tr><td><a href='{a.url}' target='_blank'>{a.title}</a></td><td>{source_name}</td><td>{published}</td><td>{a.sentiment or ''}</td></tr>")
    html.append("</table></body></html>")
    return HTMLResponse(content="".join(html))
