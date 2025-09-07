from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import settings

class Base(DeclarativeBase):
    pass

# Engine with better connection handling
engine = create_engine(
    settings.DATABASE_URL, 
    pool_pre_ping=True,
    pool_recycle=3600,  # Recycle connections every hour
    pool_size=10,       # Connection pool size
    max_overflow=20,    # Maximum overflow connections
    echo=settings.DEBUG  # SQL logging in debug mode
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
