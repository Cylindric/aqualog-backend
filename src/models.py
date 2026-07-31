from __future__ import annotations

import uuid
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db import Base


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint(
            "oauth_issuer",
            "oauth_subject",
            name="uq_users_oauth_issuer_subject",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid4)
    oauth_issuer: Mapped[str] = mapped_column(String(255), nullable=False)
    oauth_subject: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    bio: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
        onupdate=_utc_now,
    )


class Aquarium(Base):
    __tablename__ = "aquariums"
    __table_args__ = (
        UniqueConstraint(
            "owner_user_id",
            "name",
            name="uq_aquariums_owner_name",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid4)
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    type: Mapped[str] = mapped_column(String(24), nullable=False)
    volume_liters: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
        onupdate=_utc_now,
    )


class Parameter(Base):
    __tablename__ = "parameters"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid4)
    slug: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
        onupdate=_utc_now,
    )


class Unit(Base):
    __tablename__ = "units"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid4)
    # URL-safe routing key: lowercase, "/" replaced with "_" (e.g. "mg_l"). Derived
    # from `unit` at creation time — see src/unit_slug.py::slugify_unit.
    slug: Mapped[str] = mapped_column(String(16), nullable=False, unique=True, index=True)
    # The actual unit notation as used in measurement data (e.g. "mg/L", "pH").
    unit: Mapped[str] = mapped_column(String(16), nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
        onupdate=_utc_now,
    )


class ParameterUnit(Base):
    __tablename__ = "parameter_units"

    parameter_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("parameters.id", ondelete="CASCADE"),
        primary_key=True,
    )
    unit_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("units.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    is_canonical: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


Index(
    "uq_parameter_units_canonical_per_parameter",
    ParameterUnit.parameter_id,
    unique=True,
    sqlite_where=ParameterUnit.is_canonical.is_(True),
    postgresql_where=ParameterUnit.is_canonical.is_(True),
)


class AquariumParameterThreshold(Base):
    __tablename__ = "aquarium_parameter_thresholds"
    __table_args__ = (
        UniqueConstraint(
            "aquarium_id",
            "parameter_id",
            name="uq_aquarium_parameter_thresholds_aquarium_parameter",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid4)
    aquarium_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("aquariums.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parameter_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("parameters.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    target: Mapped[float | None] = mapped_column(Float, nullable=True)
    min: Mapped[float | None] = mapped_column(Float, nullable=True)
    max: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
        onupdate=_utc_now,
    )


class AquariumMeasurement(Base):
    __tablename__ = "aquarium_measurements"
    __table_args__ = (
        UniqueConstraint(
            "aquarium_id",
            "parameter_id",
            "measured_at",
            name="uq_aquarium_measurements_aquarium_parameter_measured_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid4)
    aquarium_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("aquariums.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parameter_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("parameters.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("units.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    raw_value: Mapped[float] = mapped_column(Float, nullable=False)
    raw_unit_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("units.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    measured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )

    unit: Mapped[Unit] = relationship("Unit", foreign_keys=[unit_id])
    raw_unit: Mapped[Unit] = relationship("Unit", foreign_keys=[raw_unit_id])
