"""
Configuration loader for the app.

Loads environment variables from .env (if present) and provides safe defaults.
By default a local SQLite DB is used (sqlite:///./perspectiva.db) unless DATABASE_URL is set.
"""

import os
from dotenv import load_dotenv
from typing import List

load_dotenv()

def _getenv(name: str, default: str = "") -> str:
    return os.getenv(name, default)

class Settings:
    DATABASE_URL: str = _getenv("DATABASE_URL") or "sqlite:///./perspectiva.db"
    # FEEDS: list of RSS feed URLs
    FEEDS: List[str] = [f.strip() for f in _getenv("FEEDS", "https://feeds.bbci.co.uk/news/rss.xml,https://rss.cnn.com/rss/edition.rss").split(",") if f.strip()]
    # Ingestion
    FETCH_INTERVAL_SECONDS: int = int(_getenv("FETCH_INTERVAL_SECONDS", "300"))
    MAX_ITEMS_PER_FEED: int = int(_getenv("MAX_ITEMS_PER_FEED", "15"))
    SUMMARY_SENTENCES: int = int(_getenv("SUMMARY_SENTENCES", "3"))
    # Logging
    LOG_LEVEL: str = _getenv("LOG_LEVEL", "INFO").upper()

settings = Settings()

