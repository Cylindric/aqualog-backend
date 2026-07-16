from __future__ import annotations

from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from aqualog_api.config import Settings


class Base(DeclarativeBase):
    pass


_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def _normalize_database_url(url: str) -> str:
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def get_database_url(settings: Settings) -> str:
    if settings.app_env == "test" and settings.test_database_url:
        return settings.test_database_url
    return settings.database_url


def configure_database(settings: Settings) -> None:
    global _engine, _session_factory

    if _engine is not None and _session_factory is not None:
        return

    database_url = _normalize_database_url(get_database_url(settings))
    if database_url.startswith("sqlite"):
        db_path = make_url(database_url).database
        if db_path and db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    connect_args: dict[str, object] = {}
    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    _engine = create_engine(
        database_url,
        future=True,
        pool_pre_ping=True,
        connect_args=connect_args,
    )
    _session_factory = sessionmaker(
        bind=_engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        future=True,
    )


def init_database(settings: Settings) -> None:
    # Import models here so metadata is complete before any create_all calls.
    from aqualog_api import models  # noqa: F401

    configure_database(settings)
    if _engine is None:
        raise RuntimeError("Database engine is not configured")

    if settings.app_env == "test":
        Base.metadata.create_all(bind=_engine)

    with _engine.connect() as connection:
        connection.execute(text("SELECT 1"))


def get_session() -> Generator[Session, None, None]:
    if _session_factory is None:
        raise RuntimeError("Database is not configured")

    session = _session_factory()
    try:
        yield session
    finally:
        session.close()


def reset_database() -> None:
    global _engine, _session_factory

    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None
