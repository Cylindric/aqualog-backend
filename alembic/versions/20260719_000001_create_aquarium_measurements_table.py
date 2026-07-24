"""create aquarium measurements table

Revision ID: 20260719_000001
Revises: 20260717_000001
Create Date: 2026-07-19 00:00:01
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260719_000001"
down_revision: Union[str, Sequence[str], None] = "20260717_000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "aquarium_measurements",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("aquarium_id", sa.String(length=36), nullable=False),
        sa.Column("parameter", sa.String(length=32), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(length=16), nullable=False),
        sa.Column("raw_value", sa.Float(), nullable=False),
        sa.Column("raw_unit", sa.String(length=16), nullable=False),
        sa.Column("measured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["aquarium_id"], ["aquariums.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "aquarium_id",
            "parameter",
            "measured_at",
            name="uq_aquarium_measurements_aquarium_parameter_measured_at",
        ),
    )
    op.create_index(
        "ix_aquarium_measurements_aquarium_id",
        "aquarium_measurements",
        ["aquarium_id"],
        unique=False,
    )
    op.create_index(
        "ix_aquarium_measurements_parameter",
        "aquarium_measurements",
        ["parameter"],
        unique=False,
    )
    op.create_index(
        "ix_aquarium_measurements_measured_at",
        "aquarium_measurements",
        ["measured_at"],
        unique=False,
    )
    op.create_index(
        "ix_aquarium_measurements_aquarium_id_measured_at",
        "aquarium_measurements",
        ["aquarium_id", "measured_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_aquarium_measurements_aquarium_id_measured_at", table_name="aquarium_measurements"
    )
    op.drop_index("ix_aquarium_measurements_measured_at", table_name="aquarium_measurements")
    op.drop_index("ix_aquarium_measurements_parameter", table_name="aquarium_measurements")
    op.drop_index("ix_aquarium_measurements_aquarium_id", table_name="aquarium_measurements")
    op.drop_table("aquarium_measurements")
