"""
database.py

SQLAlchemy engine, session factory, and declarative base for LogSense.
Uses SQLite in development (per docs/ml_design.md-adjacent architecture
notes) and swaps transparently to Postgres in production via DATABASE_URL.
"""

import sys
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

try:
    from app.core.config import settings
except ImportError:
    sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
    from app.core.config import settings

# SQLite requires check_same_thread=False to be used across FastAPI's
# threaded request handling; Postgres and other DBs don't need this.
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency: yields a DB session, always closed after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables. Called once on app startup (see main.py)."""
    from app.db import models  # noqa: F401 - ensures models are registered on Base
    Base.metadata.create_all(bind=engine)