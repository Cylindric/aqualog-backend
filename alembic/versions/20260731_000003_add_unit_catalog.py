"""add_unit_catalog

Revision ID: 20260731_000003
Revises: 20260731_000002
Create Date: 2026-07-31 00:00:03
"""

from datetime import datetime, timezone
from typing import Sequence, Union
from uuid import uuid4

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260731_000003"
down_revision: Union[str, Sequence[str], None] = "20260731_000002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UUID_TYPE = postgresql.UUID(as_uuid=True)

SEED_UNITS = [
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
]

# (parameter_slug, unit_slug, is_canonical)
SEED_PARAMETER_UNITS = [
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
]

IX_UNITS_SLUG_LOWER = "ix_units_slug_lower"
UQ_PARAMETER_UNITS_CANONICAL = "uq_parameter_units_canonical_per_parameter"


def upgrade() -> None:
    op.create_table(
        "units",
        sa.Column("id", UUID_TYPE, nullable=False),
        sa.Column("slug", sa.String(length=16), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(IX_UNITS_SLUG_LOWER, "units", [sa.text("lower(slug)")], unique=True)

    units_table = sa.table(
        "units",
        sa.column("id", UUID_TYPE),
        sa.column("slug", sa.String),
        sa.column("display_name", sa.String),
        sa.column("description", sa.String),
        sa.column("created_at", sa.DateTime),
        sa.column("updated_at", sa.DateTime),
    )
    now = datetime.now(timezone.utc)
    op.bulk_insert(
        units_table,
        [
            {
                "id": uuid4(),
                "slug": slug,
                "display_name": display_name,
                "description": description,
                "created_at": now,
                "updated_at": now,
            }
            for slug, display_name, description in SEED_UNITS
        ],
    )

    op.create_table(
        "parameter_units",
        sa.Column("parameter_id", UUID_TYPE, nullable=False),
        sa.Column("unit_id", UUID_TYPE, nullable=False),
        sa.Column("is_canonical", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.PrimaryKeyConstraint("parameter_id", "unit_id"),
        sa.ForeignKeyConstraint(
            ["parameter_id"],
            ["parameters.id"],
            name="fk_parameter_units_parameter_parameters",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["unit_id"],
            ["units.id"],
            name="fk_parameter_units_unit_units",
            ondelete="RESTRICT",
        ),
    )
    op.create_index(
        UQ_PARAMETER_UNITS_CANONICAL,
        "parameter_units",
        ["parameter_id"],
        unique=True,
        postgresql_where=sa.text("is_canonical"),
    )

    for parameter_slug, unit_slug, is_canonical in SEED_PARAMETER_UNITS:
        op.execute(
            sa.text(
                "INSERT INTO parameter_units (parameter_id, unit_id, is_canonical) "
                "SELECT p.id, u.id, :is_canonical FROM parameters p, units u "
                "WHERE p.slug = :parameter_slug AND u.slug = :unit_slug"
            ).bindparams(
                is_canonical=is_canonical,
                parameter_slug=parameter_slug,
                unit_slug=unit_slug,
            )
        )


def downgrade() -> None:
    op.drop_index(UQ_PARAMETER_UNITS_CANONICAL, table_name="parameter_units")
    op.drop_table("parameter_units")
    op.drop_index(IX_UNITS_SLUG_LOWER, table_name="units")
    op.drop_table("units")
