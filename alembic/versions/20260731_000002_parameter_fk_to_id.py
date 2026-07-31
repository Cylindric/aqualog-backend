"""parameter fk to id

Revision ID: 20260731_000002
Revises: 20260731_000001
Create Date: 2026-07-31 00:00:02
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260731_000002"
down_revision: Union[str, Sequence[str], None] = "20260731_000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

FK_MEASUREMENTS_PARAMETER = "fk_aquarium_measurements_parameter_parameters"
FK_THRESHOLDS_PARAMETER = "fk_aquarium_parameter_thresholds_parameter_parameters"

IX_MEASUREMENTS_PARAMETER = "ix_aquarium_measurements_parameter"
IX_THRESHOLDS_PARAMETER = "ix_aquarium_parameter_thresholds_parameter"

UQ_MEASUREMENTS = "uq_aquarium_measurements_aquarium_parameter_measured_at"
UQ_THRESHOLDS = "uq_aquarium_parameter_thresholds_aquarium_parameter"

UUID_TYPE = postgresql.UUID(as_uuid=True)
STRING_32 = sa.String(length=32)


def upgrade() -> None:
    op.drop_constraint(UQ_MEASUREMENTS, "aquarium_measurements", type_="unique")
    op.drop_constraint(UQ_THRESHOLDS, "aquarium_parameter_thresholds", type_="unique")
    op.drop_constraint(FK_MEASUREMENTS_PARAMETER, "aquarium_measurements", type_="foreignkey")
    op.drop_constraint(FK_THRESHOLDS_PARAMETER, "aquarium_parameter_thresholds", type_="foreignkey")
    op.drop_index(IX_MEASUREMENTS_PARAMETER, table_name="aquarium_measurements")
    op.drop_index(IX_THRESHOLDS_PARAMETER, table_name="aquarium_parameter_thresholds")

    op.add_column("aquarium_measurements", sa.Column("parameter_id", UUID_TYPE, nullable=True))
    op.add_column(
        "aquarium_parameter_thresholds", sa.Column("parameter_id", UUID_TYPE, nullable=True)
    )

    op.execute(
        "UPDATE aquarium_measurements SET parameter_id = parameters.id "
        "FROM parameters WHERE parameters.slug = aquarium_measurements.parameter"
    )
    op.execute(
        "UPDATE aquarium_parameter_thresholds SET parameter_id = parameters.id "
        "FROM parameters WHERE parameters.slug = aquarium_parameter_thresholds.parameter"
    )

    op.alter_column("aquarium_measurements", "parameter_id", nullable=False)
    op.alter_column("aquarium_parameter_thresholds", "parameter_id", nullable=False)

    op.drop_column("aquarium_measurements", "parameter")
    op.drop_column("aquarium_parameter_thresholds", "parameter")

    op.create_index(
        IX_MEASUREMENTS_PARAMETER, "aquarium_measurements", ["parameter_id"], unique=False
    )
    op.create_index(
        IX_THRESHOLDS_PARAMETER, "aquarium_parameter_thresholds", ["parameter_id"], unique=False
    )

    op.create_foreign_key(
        FK_MEASUREMENTS_PARAMETER,
        "aquarium_measurements",
        "parameters",
        ["parameter_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        FK_THRESHOLDS_PARAMETER,
        "aquarium_parameter_thresholds",
        "parameters",
        ["parameter_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.create_unique_constraint(
        UQ_MEASUREMENTS,
        "aquarium_measurements",
        ["aquarium_id", "parameter_id", "measured_at"],
    )
    op.create_unique_constraint(
        UQ_THRESHOLDS,
        "aquarium_parameter_thresholds",
        ["aquarium_id", "parameter_id"],
    )


def downgrade() -> None:
    op.drop_constraint(UQ_MEASUREMENTS, "aquarium_measurements", type_="unique")
    op.drop_constraint(UQ_THRESHOLDS, "aquarium_parameter_thresholds", type_="unique")
    op.drop_constraint(FK_MEASUREMENTS_PARAMETER, "aquarium_measurements", type_="foreignkey")
    op.drop_constraint(FK_THRESHOLDS_PARAMETER, "aquarium_parameter_thresholds", type_="foreignkey")
    op.drop_index(IX_MEASUREMENTS_PARAMETER, table_name="aquarium_measurements")
    op.drop_index(IX_THRESHOLDS_PARAMETER, table_name="aquarium_parameter_thresholds")

    op.add_column("aquarium_measurements", sa.Column("parameter", STRING_32, nullable=True))
    op.add_column("aquarium_parameter_thresholds", sa.Column("parameter", STRING_32, nullable=True))

    op.execute(
        "UPDATE aquarium_measurements SET parameter = parameters.slug "
        "FROM parameters WHERE parameters.id = aquarium_measurements.parameter_id"
    )
    op.execute(
        "UPDATE aquarium_parameter_thresholds SET parameter = parameters.slug "
        "FROM parameters WHERE parameters.id = aquarium_parameter_thresholds.parameter_id"
    )

    op.alter_column("aquarium_measurements", "parameter", nullable=False)
    op.alter_column("aquarium_parameter_thresholds", "parameter", nullable=False)

    op.drop_column("aquarium_measurements", "parameter_id")
    op.drop_column("aquarium_parameter_thresholds", "parameter_id")

    op.create_index(IX_MEASUREMENTS_PARAMETER, "aquarium_measurements", ["parameter"], unique=False)
    op.create_index(
        IX_THRESHOLDS_PARAMETER, "aquarium_parameter_thresholds", ["parameter"], unique=False
    )

    op.create_foreign_key(
        FK_MEASUREMENTS_PARAMETER,
        "aquarium_measurements",
        "parameters",
        ["parameter"],
        ["slug"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        FK_THRESHOLDS_PARAMETER,
        "aquarium_parameter_thresholds",
        "parameters",
        ["parameter"],
        ["slug"],
        ondelete="RESTRICT",
    )

    op.create_unique_constraint(
        UQ_MEASUREMENTS,
        "aquarium_measurements",
        ["aquarium_id", "parameter", "measured_at"],
    )
    op.create_unique_constraint(
        UQ_THRESHOLDS,
        "aquarium_parameter_thresholds",
        ["aquarium_id", "parameter"],
    )
