import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    DATABASE_URL = os.getenv("DATABASE_URL") or f"postgresql+psycopg2://{os.getenv('POSTGRES_USER','perspectiva')}:{os.getenv('POSTGRES_PASSWORD','perspectiva')}@localhost:5432/{os.getenv('POSTGRES_DB','perspectiva')}"
    FEEDS = [u.strip() for u in os.getenv("FEEDS", "").split(",") if u.strip()]
    FETCH_INTERVAL_SECONDS = int(os.getenv("FETCH_INTERVAL_SECONDS", "600"))
    MAX_ITEMS_PER_FEED = int(os.getenv("MAX_ITEMS_PER_FEED", "10"))
    SUMMARY_SENTENCES = int(os.getenv("SUMMARY_SENTENCES", "3"))
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

settings = Settings()
