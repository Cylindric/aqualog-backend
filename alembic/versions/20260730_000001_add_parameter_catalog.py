"""add_parameter_catalog

Revision ID: 20260730_000001
Revises: 20260726_000002
Create Date: 2026-07-30 00:00:01
"""

from datetime import datetime, timezone
from typing import Sequence, Union
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260730_000001"
down_revision: Union[str, Sequence[str], None] = "20260726_000002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SEED_PARAMETERS = [
    (
        "salinity",
        "Salinity",
        "Salt concentration of aquarium water, measured in parts per thousand (ppt).",
    ),
    (
        "phosphate",
        "Phosphate",
        "Phosphate concentration, a key nutrient indicator for algae control, "
        "measured in parts per million (ppm).",
    ),
    (
        "temperature",
        "Temperature",
        "Water temperature, measured in degrees Celsius.",
    ),
    (
        "calcium",
        "Calcium",
        "Calcium concentration, important for coral and invertebrate growth, "
        "measured in parts per million (ppm).",
    ),
    (
        "ammonia",
        "Ammonia",
        "Ammonia concentration, a key indicator of biological filtration health, "
        "measured in milligrams per litre (mg/L).",
    ),
    (
        "nitrite",
        "Nitrite",
        "Nitrite concentration, an intermediate nitrogen cycle byproduct, "
        "measured in parts per million (ppm).",
    ),
    (
        "nitrate",
        "Nitrate",
        "Nitrate concentration, the end product of the nitrogen cycle, "
        "measured in parts per million (ppm).",
    ),
    (
        "ph",
        "pH",
        "Acidity/alkalinity of the water on the pH scale.",
    ),
    (
        "alkalinity",
        "Alkalinity",
        "Carbonate hardness / buffering capacity, measured in degrees KH (dKH).",
    ),
    (
        "magnesium",
        "Magnesium",
        "Magnesium concentration, which supports calcium and alkalinity stability, "
        "measured in parts per million (ppm).",
    ),
]

FK_MEASUREMENTS = "fk_aquarium_measurements_parameter_parameters"
FK_THRESHOLDS = "fk_aquarium_parameter_thresholds_parameter_parameters"


def upgrade() -> None:
    op.create_table(
        "parameters",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("slug", sa.String(length=32), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_parameters_slug"), "parameters", ["slug"], unique=True)

    parameters_table = sa.table(
        "parameters",
        sa.column("id", sa.String),
        sa.column("slug", sa.String),
        sa.column("display_name", sa.String),
        sa.column("description", sa.String),
        sa.column("created_at", sa.DateTime),
        sa.column("updated_at", sa.DateTime),
    )
    now = datetime.now(timezone.utc)
    op.bulk_insert(
        parameters_table,
        [
            {
                "id": str(uuid4()),
                "slug": slug,
                "display_name": display_name,
                "description": description,
                "created_at": now,
                "updated_at": now,
            }
            for slug, display_name, description in SEED_PARAMETERS
        ],
    )

    op.create_foreign_key(
        FK_MEASUREMENTS,
        "aquarium_measurements",
        "parameters",
        ["parameter"],
        ["slug"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        FK_THRESHOLDS,
        "aquarium_parameter_thresholds",
        "parameters",
        ["parameter"],
        ["slug"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint(FK_THRESHOLDS, "aquarium_parameter_thresholds", type_="foreignkey")
    op.drop_constraint(FK_MEASUREMENTS, "aquarium_measurements", type_="foreignkey")
    op.drop_index(op.f("ix_parameters_slug"), table_name="parameters")
    op.drop_table("parameters")
