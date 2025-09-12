"""
Database initialization and session provider.

Uses SQLAlchemy. By default uses SQLite file perspectiva.db in the project root.
If you want to use Postgres, set DATABASE_URL in environment (e.g. in .env).
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from app.config import settings
import logging

logger = logging.getLogger("app.db")

# create engine with check_same_thread disabled for SQLite when using multiple threads
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
Base = declarative_base()

def get_db() -> Session:
    """
    Yield a SQLAlchemy session (use as dependency in FastAPI).
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Create tables. Safe to call on startup."""
    import sqlalchemy
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database initialized: %s", settings.DATABASE_URL)
    except sqlalchemy.exc.SQLAlchemyError as e:
        logger.exception("Failed to initialize database: %s", e)
        raise
