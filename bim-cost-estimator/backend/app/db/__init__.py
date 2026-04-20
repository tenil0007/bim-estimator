"""
Database Connection & Session Management
-----------------------------------------
SQLAlchemy async engine setup with session lifecycle management.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import get_settings


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


def get_engine():
    """Create SQLAlchemy engine."""
    settings = get_settings()
    connect_args = {}

    if settings.database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    engine = create_engine(
        settings.database_url,
        connect_args=connect_args,
        echo=settings.debug,
    )
    return engine


engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Dependency injection for database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)
