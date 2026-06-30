"""Database engine, session factory and declarative base."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,   # drop dead connections automatically
    pool_recycle=3600,    # recycle connections every hour (MySQL wait_timeout)
    echo=False,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Base class for all ORM models."""


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_all_tables() -> None:
    """Create all tables. Models must be imported before calling this."""
    from . import models  # noqa: F401  (registers all models on Base.metadata)

    Base.metadata.create_all(bind=engine)
