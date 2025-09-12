"""
Feed ingestion utilities.

Provides:
 - run_once(db_session) : fetch configured feeds once and insert/update entries
 - run_forever() : spawn a background thread that periodically fetches feeds

Notes:
 - This implementation uses only feedparser + requests to keep dependencies light.
 - Full-text extraction is implemented with a small fallback (strip tags). For better extraction,
   libraries such as trafilatura or newspaper3k can be plugged in later.
 - Sentiment uses a very small naive approach (word lists) to avoid heavy dependencies.
"""

import logging
import threading
import time
import hashlib
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

import feedparser
import requests
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Source, Article

logger = logging.getLogger("app.ingest")
logger.setLevel(getattr(logging, settings.LOG_LEVEL, "INFO"))

# small lexicons for naive sentiment scoring
_POS_WORDS = {"good", "great", "positive", "up", "win", "benefit", "beneficial", "growth", "success"}
_NEG_WORDS = {"bad", "worse", "loss", "down", "decline", "negative", "risk", "crash", "drop"}


def _simple_sentiment(text: Optional[str]) -> str:
    """Return 'positive'|'negative'|'neutral' based on simple bag-of-words counts."""
    if not text:
        return "neutral"
    text_lower = text.lower()
    pos = sum(text_lower.count(w) for w in _POS_WORDS)
    neg = sum(text_lower.count(w) for w in _NEG_WORDS)
    if pos > neg:
        return "positive"
    if neg > pos:
        return "negative"
    return "neutral"


def _hash_url(url: str) -> str:
    """Deterministic sha256 hex digest of url for unique keying."""
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def _strip_html_tags(html: str) -> str:
    """Very simple HTML-to-text cleanup (no external deps)."""
    import re
    # remove scripts/styles
    text = re.sub(r"(?is)<(script|style).*?>.*?(</\1>)", " ", html)
    # remove tags
    text = re.sub(r"(?s)<[^>]*>", " ", text)
    # collapse whitespace
    text = " ".join(text.split())
    return text.strip()


def _get_full_text(url: str) -> Optional[str]:
    """Attempt to fetch article and extract readable text. Simple fallback only."""
    try:
        resp = requests.get(url, timeout=8)
        if resp.status_code != 200:
            logger.debug("Non-200 fetching %s: %s", url, resp.status_code)
            return None
        # naive extraction
        return _strip_html_tags(resp.text)
    except Exception as e:
        logger.debug("Error fetching full text for %s: %s", url, e)
        return None


def _summarize(text: Optional[str], sentences: int = 3) -> Optional[str]:
    """Very simple summarizer: return first N sentences by splitting on punctuation."""
    if not text:
        return None
    import re
    parts = re.split(r'(?<=[.!?])\s+', text)
    summary = " ".join(parts[:max(1, sentences)])
    return summary.strip()


def upsert_source(db: Session, name: str, base_url: str, rss_url: str) -> Source:
    """Create or find a Source row for an RSS feed."""
    src = db.query(Source).filter(Source.rss_url == rss_url).first()
    if src:
        # update basic metadata if changed
        changed = False
        if src.name != name:
            src.name = name
            changed = True
        if src.base_url != base_url:
            src.base_url = base_url
            changed = True
        if changed:
            db.add(src)
            db.commit()
            db.refresh(src)
        return src
    src = Source(name=name, base_url=base_url, rss_url=rss_url)
    db.add(src)
    db.commit()
    db.refresh(src)
    return src


def run_once(db: Session):
    """
    Fetch all configured feeds once and save new articles.

    This function is idempotent with respect to article URL: each URL's hash is used to
    prevent duplicate inserts.
    """
    feeds = settings.FEEDS
    max_items = settings.MAX_ITEMS_PER_FEED

    logger.info("Starting single fetch for %d feeds", len(feeds))
    for feed_url in feeds:
        logger.info("Parsing feed %s", feed_url)
        try:
            parsed = feedparser.parse(feed_url)
        except Exception as e:
            logger.exception("Failed to parse feed %s: %s", feed_url, e)
            continue

        if parsed.bozo:
            logger.warning("Feed parser reported bozo for %s: %s", feed_url, getattr(parsed, "bozo_exception", None))

        entries = parsed.entries[:max_items]
        for entry in entries:
            try:
                title = entry.get("title", "Untitled")
                link = entry.get("link")
                published = None
                if "published_parsed" in entry and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6])
                elif "updated_parsed" in entry and entry.updated_parsed:
                    published = datetime(*entry.updated_parsed[:6])

                if not link:
                    logger.debug("Skipping entry with no link: %s", title)
                    continue

                url_hash = _hash_url(link)
                existing = db.query(Article).filter(Article.url_hash == url_hash).first()
                if existing:
                    logger.debug("Skipping already-stored article %s", link)
                    continue

                # derive a source name and base_url heuristically
                parsed_url = urlparse(link)
                base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
                source_name = parsed.get("title") or parsed_url.netloc

                src = upsert_source(db, name=source_name, base_url=base_url, rss_url=feed_url)

                # full text extraction (best-effort)
                full_text = None
                if "content" in entry and entry.content:
                    # feed may contain content
                    contents = entry.content[0].value if isinstance(entry.content, list) else entry.content
                    full_text = _strip_html_tags(contents)
                if not full_text:
                    # try feed summary
                    summary_html = entry.get("summary") or entry.get("description")
                    if summary_html:
                        full_text = _strip_html_tags(summary_html)
                if not full_text:
                    # attempt to fetch article page and extract text
                    full_text = _get_full_text(link)

                # generate summary & sentiment
                summary = _summarize(full_text, sentences=settings.SUMMARY_SENTENCES)
                sentiment = _simple_sentiment(summary or full_text or title)

                article = Article(
                    source_id=src.id,
                    title=title,
                    url=link,
                    url_hash=url_hash,
                    published_at=published,
                    full_text=full_text,
                    summary=summary,
                    sentiment=sentiment,
                )
                db.add(article)
                db.commit()
                db.refresh(article)
                logger.info("Inserted article id=%s title=%s", article.id, article.title[:60])

            except Exception as e:
                # don't let one bad entry stop the feed
                logger.exception("Failed to process entry in feed %s: %s", feed_url, e)


def _background_loop(stop_event: threading.Event):
    import sqlalchemy
    # create a new DB session in this thread
    from app.db import SessionLocal
    db = SessionLocal()
    try:
        while not stop_event.is_set():
            try:
                run_once(db)
            except Exception:
                logger.exception("Unexpected error in ingestion run_once()")
            # sleep with small increments so stop_event can be noticed
            total = settings.FETCH_INTERVAL_SECONDS
            slept = 0
            while slept < total:
                if stop_event.is_set():
                    break
                time.sleep(1)
                slept += 1
    finally:
        db.close()


_ingest_thread = None
_ingest_stop = None

def run_forever(start_immediately: bool = True):
    """
    Start a background thread to run ingestion periodically.

    Returns a dict with thread and stop_event in case the caller wants to stop the loop.
    If invoked multiple times, returns existing thread info.
    """
    global _ingest_thread, _ingest_stop
    if _ingest_thread and _ingest_thread.is_alive():
        return {"thread": _ingest_thread, "stop_event": _ingest_stop}

    _ingest_stop = threading.Event()
    _ingest_thread = threading.Thread(target=_background_loop, args=(_ingest_stop,), daemon=True, name="ingest-thread")
    if start_immediately:
        _ingest_thread.start()
    return {"thread": _ingest_thread, "stop_event": _ingest_stop}
