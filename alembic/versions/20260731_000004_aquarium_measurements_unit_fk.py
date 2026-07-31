"""aquarium_measurements_unit_fk

Revision ID: 20260731_000004
Revises: 20260731_000003
Create Date: 2026-07-31 00:00:04
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260731_000004"
down_revision: Union[str, Sequence[str], None] = "20260731_000003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UUID_TYPE = postgresql.UUID(as_uuid=True)
STRING_16 = sa.String(length=16)

FK_UNIT = "fk_aquarium_measurements_unit_units"
FK_RAW_UNIT = "fk_aquarium_measurements_raw_unit_units"
IX_UNIT = "ix_aquarium_measurements_unit_id"
IX_RAW_UNIT = "ix_aquarium_measurements_raw_unit_id"


def upgrade() -> None:
    op.add_column("aquarium_measurements", sa.Column("unit_id", UUID_TYPE, nullable=True))
    op.add_column("aquarium_measurements", sa.Column("raw_unit_id", UUID_TYPE, nullable=True))

    # Case-insensitive join: existing `unit`/`raw_unit` values may be stored in a
    # different casing than the seeded `units.slug` (e.g. `raw_unit='mg/l'` from the
    # measurement create validator lowercasing input, vs. seeded slug `mg/L`).
    op.execute(
        "UPDATE aquarium_measurements SET unit_id = units.id "
        "FROM units WHERE lower(units.slug) = lower(aquarium_measurements.unit)"
    )
    op.execute(
        "UPDATE aquarium_measurements SET raw_unit_id = units.id "
        "FROM units WHERE lower(units.slug) = lower(aquarium_measurements.raw_unit)"
    )

    op.alter_column("aquarium_measurements", "unit_id", nullable=False)
    op.alter_column("aquarium_measurements", "raw_unit_id", nullable=False)

    op.drop_column("aquarium_measurements", "unit")
    op.drop_column("aquarium_measurements", "raw_unit")

    op.create_index(IX_UNIT, "aquarium_measurements", ["unit_id"], unique=False)
    op.create_index(IX_RAW_UNIT, "aquarium_measurements", ["raw_unit_id"], unique=False)

    op.create_foreign_key(
        FK_UNIT,
        "aquarium_measurements",
        "units",
        ["unit_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        FK_RAW_UNIT,
        "aquarium_measurements",
        "units",
        ["raw_unit_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint(FK_UNIT, "aquarium_measurements", type_="foreignkey")
    op.drop_constraint(FK_RAW_UNIT, "aquarium_measurements", type_="foreignkey")
    op.drop_index(IX_UNIT, table_name="aquarium_measurements")
    op.drop_index(IX_RAW_UNIT, table_name="aquarium_measurements")

    op.add_column("aquarium_measurements", sa.Column("unit", STRING_16, nullable=True))
    op.add_column("aquarium_measurements", sa.Column("raw_unit", STRING_16, nullable=True))

    op.execute(
        "UPDATE aquarium_measurements SET unit = units.slug "
        "FROM units WHERE units.id = aquarium_measurements.unit_id"
    )
    op.execute(
        "UPDATE aquarium_measurements SET raw_unit = units.slug "
        "FROM units WHERE units.id = aquarium_measurements.raw_unit_id"
    )

    op.alter_column("aquarium_measurements", "unit", nullable=False)
    op.alter_column("aquarium_measurements", "raw_unit", nullable=False)

    op.drop_column("aquarium_measurements", "unit_id")
    op.drop_column("aquarium_measurements", "raw_unit_id")
