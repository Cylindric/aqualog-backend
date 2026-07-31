from __future__ import annotations

from collections.abc import Generator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from src.config import Settings


class Base(DeclarativeBase):
    pass


_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None

# Mirrors the seed data inserted by the `20260730_000001_add_parameter_catalog`
# Alembic migration. Tests build their schema from model metadata rather than
# running migrations, so the catalog must be seeded here to match.
_SEED_PARAMETERS = (
    ("salinity", "Salinity", "Salt concentration of aquarium water, measured in ppt."),
    ("phosphate", "Phosphate", "Phosphate concentration, measured in ppm."),
    ("temperature", "Temperature", "Water temperature, measured in degrees Celsius."),
    ("calcium", "Calcium", "Calcium concentration, measured in ppm."),
    ("ammonia", "Ammonia", "Ammonia concentration, measured in mg/L."),
    ("nitrite", "Nitrite", "Nitrite concentration, measured in ppm."),
    ("nitrate", "Nitrate", "Nitrate concentration, measured in ppm."),
    ("ph", "pH", "Acidity/alkalinity of the water on the pH scale."),
    ("alkalinity", "Alkalinity", "Carbonate hardness/buffering capacity, measured in dKH."),
    ("magnesium", "Magnesium", "Magnesium concentration, measured in ppm."),
)

# Mirrors the seed data inserted by the `20260731_000003_add_unit_catalog`
# Alembic migration. Tests build their schema from model metadata rather than
# running migrations, so the catalog must be seeded here to match.
_SEED_UNITS = (
    ("ppt", "Parts per Thousand", "Salinity concentration, measured in parts per thousand."),
    ("sg", "Specific Gravity", "Salinity measured as specific gravity relative to fresh water."),
    ("celsius", "Celsius", "Temperature, measured in degrees Celsius."),
    ("fahrenheit", "Fahrenheit", "Temperature, measured in degrees Fahrenheit."),
    ("ppm", "Parts per Million", "Concentration, measured in parts per million."),
    ("mg/L", "Milligrams per Litre", "Concentration, measured in milligrams per litre."),
    ("pH", "pH", "Acidity/alkalinity of the water on the pH scale."),
    ("dKH", "Degrees KH", "Carbonate hardness / buffering capacity, measured in degrees KH."),
    ("L", "Litres", "Volume, measured in litres."),
    ("gal_us", "US Gallons", "Volume, measured in US gallons."),
)

# (parameter_slug, unit_slug, is_canonical)
_SEED_PARAMETER_UNITS = (
    ("salinity", "ppt", True),
    ("salinity", "sg", False),
    ("temperature", "celsius", True),
    ("temperature", "fahrenheit", False),
    ("phosphate", "ppm", True),
    ("calcium", "ppm", True),
    ("ammonia", "mg/L", True),
    ("nitrite", "ppm", True),
    ("nitrate", "ppm", True),
    ("ph", "pH", True),
    ("alkalinity", "dKH", True),
    ("magnesium", "ppm", True),
)


def _enable_sqlite_foreign_keys(dbapi_connection, connection_record) -> None:
    if type(dbapi_connection).__module__.startswith("sqlite3"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def _normalize_database_url(url: str) -> str:
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def get_database_url(settings: Settings) -> str:
    uses_test_db = settings.app_env == "test" or "test_database_url" in settings.model_fields_set
    if uses_test_db and settings.test_database_url:
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
    if database_url.startswith("sqlite"):
        event.listen(_engine, "connect", _enable_sqlite_foreign_keys)
    _session_factory = sessionmaker(
        bind=_engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        future=True,
    )


def init_database(settings: Settings) -> None:
    # Import models here so metadata is complete before any create_all calls.
    from src import models  # noqa: F401

    configure_database(settings)
    if _engine is None:
        raise RuntimeError("Database engine is not configured")

    if settings.app_env == "test":
        Base.metadata.create_all(bind=_engine)
        _seed_parameters(models.Parameter)
        _seed_units(models.Unit)
        _seed_parameter_units(models.Parameter, models.Unit, models.ParameterUnit)

    with _engine.connect() as connection:
        connection.execute(text("SELECT 1"))


def _seed_parameters(parameter_model: type) -> None:
    if _session_factory is None:
        return

    session = _session_factory()
    try:
        if session.query(parameter_model).first() is not None:
            return
        now = datetime.now(timezone.utc)
        session.add_all(
            parameter_model(
                slug=slug,
                display_name=display_name,
                description=description,
                created_at=now,
                updated_at=now,
            )
            for slug, display_name, description in _SEED_PARAMETERS
        )
        session.commit()
    finally:
        session.close()


def _seed_units(unit_model: type) -> None:
    if _session_factory is None:
        return

    session = _session_factory()
    try:
        if session.query(unit_model).first() is not None:
            return
        now = datetime.now(timezone.utc)
        session.add_all(
            unit_model(
                slug=slug,
                display_name=display_name,
                description=description,
                created_at=now,
                updated_at=now,
            )
            for slug, display_name, description in _SEED_UNITS
        )
        session.commit()
    finally:
        session.close()


def _seed_parameter_units(
    parameter_model: Any, unit_model: Any, parameter_unit_model: type
) -> None:
    if _session_factory is None:
        return

    session = _session_factory()
    try:
        if session.query(parameter_unit_model).first() is not None:
            return
        for parameter_slug, unit_slug, is_canonical in _SEED_PARAMETER_UNITS:
            parameter_id = (
                session.query(parameter_model.id)
                .filter(parameter_model.slug == parameter_slug)
                .scalar()
            )
            unit_id = session.query(unit_model.id).filter(unit_model.slug == unit_slug).scalar()
            session.add(
                parameter_unit_model(
                    parameter_id=parameter_id,
                    unit_id=unit_id,
                    is_canonical=is_canonical,
                )
            )
        session.commit()
    finally:
        session.close()


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
