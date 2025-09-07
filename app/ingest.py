import hashlib
import logging
import time
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

import feedparser
import trafilatura
import requests
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.db import SessionLocal
from app.models import Source, Article
from app.config import settings

# Configure logging
log = logging.getLogger("ingest")
log.setLevel(getattr(logging, settings.LOG_LEVEL))

sent_analyzer = SentimentIntensityAnalyzer()

DEFAULT_SOURCES = {
    "BBC": {"base_url": "https://www.bbc.co.uk", "rss": "https://feeds.bbci.co.uk/news/rss.xml"},
    "CNN": {"base_url": "https://www.cnn.com", "rss": "https://rss.cnn.com/rss/edition.rss"},
    "Reuters": {"base_url": "https://www.reuters.com", "rss": "https://www.reutersagency.com/feed/?best-topics=business-finance&post_type=best"},
}

def make_hash(url: str) -> str:
    """Generate SHA256 hash of URL for deduplication."""
    return hashlib.sha256(url.encode("utf-8")).hexdigest()

def extract_text(url: str, timeout: int = 30) -> Optional[str]:
    """Extract text content from URL with timeout and error handling."""
    try:
        downloaded = trafilatura.fetch_url(
            url, 
            no_ssl=True, 
            config=trafilatura.settings.use_config({"DEFAULT": {"DOWNLOAD_TIMEOUT": str(timeout)}})
        )
        if not downloaded:
            log.warning("Failed to download content from %s", url)
            return None
        
        text = trafilatura.extract(
            downloaded, 
            include_comments=False, 
            include_tables=False,
            favor_precision=True
        )
        return text
    except Exception as e:
        log.warning("Text extraction failed for %s: %s", url, e)
        return None

def summarize_text(text: str, sentences: int = 3) -> str:
    """Generate summary of text with fallback options."""
    if not text or len(text.strip()) < 50:
        return text
        
    try:
        parser = PlaintextParser.from_string(text, Tokenizer("english"))
        summarizer = LsaSummarizer()
        sents = summarizer(parser.document, sentences)
        summary = " ".join(str(s) for s in sents)
        if summary.strip():
            return summary
    except Exception as e:
        log.debug("LSA summarization failed: %s", e)
    
    # Fallback: naive sentence extraction
    try:
        sentences_list = [s.strip() for s in text.replace("\n", " ").split(".") if s.strip()]
        if sentences_list:
            return ". ".join(sentences_list[:sentences]) + "."
    except Exception as e:
        log.debug("Fallback summarization failed: %s", e)
    
    return text[:500] + "..." if len(text) > 500 else text

def sentiment_label(text: str) -> str:
    """Analyze sentiment of text."""
    if not text:
        return "neutral"
        
    try:
        vs = sent_analyzer.polarity_scores(text)
        compound = vs.get("compound", 0)
        if compound >= 0.05:
            return "positive"
        elif compound <= -0.05:
            return "negative"
        return "neutral"
    except Exception as e:
        log.debug("Sentiment analysis failed: %s", e)
        return "neutral"

def upsert_source(db: Session, name: str, base_url: str, rss_url: Optional[str] = None) -> Optional[Source]:
    """Create or update source with proper error handling."""
    try:
        src = db.query(Source).filter(Source.base_url == base_url).first()
        if src:
            if rss_url and src.rss_url != rss_url:
                src.rss_url = rss_url
                db.commit()
                db.refresh(src)
            return src
        
        src = Source(name=name, base_url=base_url, rss_url=rss_url)
        db.add(src)
        db.commit()
        db.refresh(src)
        return src
    except IntegrityError as e:
        db.rollback()
        log.error("Source creation failed due to integrity constraint: %s", e)
        return None
    except SQLAlchemyError as e:
        db.rollback()
        log.error("Database error in upsert_source: %s", e)
        return None

def seed_default_sources(db: Session):
    """Seed default news sources."""
    for name, cfg in DEFAULT_SOURCES.items():
        try:
            upsert_source(db, name=name, base_url=cfg["base_url"], rss_url=cfg["rss"])
        except Exception as e:
            log.error("Failed to seed source %s: %s", name, e)

def get_hostname(url: str) -> Optional[str]:
    """Extract hostname from URL safely."""
    try:
        parsed = urlparse(url)
        return parsed.netloc.lower()
    except Exception:
        return None

def fetch_once():
    """Fetch articles from all configured feeds once."""
    db = SessionLocal()
    try:
        seed_default_sources(db)
        feeds = settings.FEEDS or [cfg["rss"] for cfg in DEFAULT_SOURCES.values()]
        max_items = settings.MAX_ITEMS_PER_FEED
        
        log.info("Starting fetch cycle for %d feeds", len(feeds))
        
        for feed_url in feeds:
            try:
                log.info("Processing feed: %s", feed_url)
                fp = feedparser.parse(feed_url)
                
                if fp.bozo and fp.bozo_exception:
                    log.warning("Feed parsing warning for %s: %s", feed_url, fp.bozo_exception)
                
                entries_processed = 0
                for entry in fp.entries[:max_items]:
                    if process_feed_entry(db, entry, feed_url):
                        entries_processed += 1
                
                log.info("Processed %d entries from %s", entries_processed, feed_url)
                        
            except Exception as e:
                log.error("Failed to process feed %s: %s", feed_url, e)
                continue
                
    except Exception as e:
        log.error("Unexpected error in fetch_once: %s", e)
    finally:
        db.close()

def process_feed_entry(db: Session, entry, feed_url: str) -> bool:
    """Process a single feed entry and return True if successful."""
    try:
        url = (entry.get("link") or "").strip()
        if not url:
            return False
            
        url_h = make_hash(url)

        if db.query(Article).filter(Article.url_hash == url_h).first():
            return False

        source = find_or_create_source(db, entry, feed_url, url)
        if not source:
            log.warning("Could not determine source for %s", url)
            return False

        text = extract_text(url)
        if not text:
            text = entry.get("summary", "")
        
        if not text or len(text.strip()) < 100:
            log.debug("Skipping short article: %s", url)
            return False

        summary = summarize_text(text, sentences=settings.SUMMARY_SENTENCES)
        sentiment = sentiment_label(summary or text)
        published = parse_published_date(entry)

        article = Article(
            source_id=source.id,
            title=(entry.get("title") or "")[:800],
            url=url,
            url_hash=url_h,
            published_at=published,
            full_text=text,
            summary=summary,
            sentiment=sentiment,
            meta={"feed": feed_url, "feed_title": entry.get("title", "")}
        )
        
        db.add(article)
        db.commit()
        log.info("Stored: %s (%s)", article.title[:60], source.name)
        return True
        
    except IntegrityError:
        db.rollback()
        log.debug("Article already exists: %s", url)
        return False
    except Exception as e:
        db.rollback()
        log.error("Failed to process entry %s: %s", entry.get("link", "unknown"), e)
        return False

def find_or_create_source(db: Session, entry, feed_url: str, url: str) -> Optional[Source]:
    """Find existing source or create new one."""
    source = db.query(Source).filter(Source.rss_url == feed_url).first()
    if source:
        return source
    
    hostname = get_hostname(url)
    if hostname:
        source = db.query(Source).filter(Source.base_url.like(f"%{hostname}%")).first()
        if source:
            return source
        
        source_name = hostname.replace("www.", "").split(".")[0].title()
        base_url = f"https://{hostname}"
        return upsert_source(db, name=source_name, base_url=base_url, rss_url=feed_url)
    
    return None

def parse_published_date(entry) -> Optional[datetime]:
    """Parse published date from feed entry."""
    try:
        if entry.get("published_parsed"):
            return datetime(*entry.published_parsed[:6])
    except Exception as e:
        log.debug("Date parsing failed: %s", e)
    return None

def run_forever():
    """Run ingestion loop forever."""
    interval = max(60, int(settings.FETCH_INTERVAL_SECONDS))
    log.info("Ingestion loop started (interval=%s seconds)", interval)
    
    while True:
        start = time.time()
        try:
            fetch_once()
        except KeyboardInterrupt:
            log.info("Ingestion loop stopped by user")
            break
        except Exception as e:
            log.exception("Unexpected error in fetch_once: %s", e)
        
        elapsed = time.time() - start
        sleep_for = max(5, interval - int(elapsed))
        log.debug("Fetch cycle completed in %.2f seconds, sleeping for %d seconds", elapsed, sleep_for)
        time.sleep(sleep_for)

if __name__ == "__main__":
    logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL))
    fetch_once()
