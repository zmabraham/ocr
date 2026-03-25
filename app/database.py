"""Database connection and session management"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from typing import Generator, Optional
import logging

from fastapi import HTTPException

from .models import Base
from config import settings

logger = logging.getLogger(__name__)

# Global variables for lazy initialization
_engine = None
_SessionLocal = None


def get_engine():
    """Get or create database engine"""
    global _engine, _SessionLocal
    if _engine is None:
        # For SQLite, ensure parent directory exists
        db_url = settings.DATABASE_URL
        if db_url.startswith("sqlite:///"):
            import os
            db_path = db_url.replace("sqlite:///", "")
            db_dir = os.path.dirname(db_path)
            if db_dir:
                os.makedirs(db_dir, exist_ok=True)
            logger.info(f"SQLite database path: {db_path}")

        _engine = create_engine(
            db_url,
            poolclass=QueuePool,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            echo=settings.DEBUG,
            connect_args={"check_same_thread": False} if db_url.startswith("sqlite") else {}
        )
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
        logger.info("Database engine created successfully")
    return _engine


# Create SessionLocal class for session management
def get_SessionLocal():
    """Get SessionLocal class"""
    get_engine()  # Ensure engine is initialized
    return _SessionLocal


# Legacy compatibility - create engine on import for now
# This will be replaced with lazy loading
try:
    db_url = settings.DATABASE_URL
    if db_url.startswith("sqlite:///"):
        import os
        db_path = db_url.replace("sqlite:///", "")
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        logger.info(f"SQLite database path: {db_path}")

    engine = create_engine(
        db_url,
        poolclass=QueuePool,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        echo=settings.DEBUG,
        connect_args={"check_same_thread": False} if db_url.startswith("sqlite") else {}
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    logger.info("Legacy database engine created successfully")
except Exception as e:
    logger.warning(f"Could not create database engine: {e}")
    engine = None
    SessionLocal = None


def init_db():
    """Initialize database tables"""
    try:
        eng = get_engine()
        Base.metadata.create_all(bind=eng)
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.warning(f"Database initialization failed: {e}")
        # Don't raise - allow app to start without database


def get_db() -> Generator[Session, None, None]:
    """Dependency for FastAPI to get database session"""
    SessionLocal_class = get_SessionLocal()
    if SessionLocal_class is None:
        raise HTTPException(status_code=503, detail="Database not available")
    db = SessionLocal_class()
    try:
        yield db
    finally:
        db.close()


def reset_db():
    """Drop and recreate all tables (for development/testing)"""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    logger.info("Database reset successfully")
