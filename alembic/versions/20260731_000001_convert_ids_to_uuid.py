"""convert ids to uuid

Revision ID: 20260731_000001
Revises: 20260730_000001
Create Date: 2026-07-31 00:00:01
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260731_000001"
down_revision: Union[str, Sequence[str], None] = "20260730_000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

FK_AQUARIUMS_OWNER = "aquariums_owner_user_id_fkey"
FK_MEASUREMENTS_AQUARIUM = "aquarium_measurements_aquarium_id_fkey"
FK_THRESHOLDS_AQUARIUM = "aquarium_parameter_thresholds_aquarium_id_fkey"

UUID_TYPE = postgresql.UUID(as_uuid=True)
STRING_36 = sa.String(length=36)


def upgrade() -> None:
    op.drop_constraint(FK_THRESHOLDS_AQUARIUM, "aquarium_parameter_thresholds", type_="foreignkey")
    op.drop_constraint(FK_MEASUREMENTS_AQUARIUM, "aquarium_measurements", type_="foreignkey")
    op.drop_constraint(FK_AQUARIUMS_OWNER, "aquariums", type_="foreignkey")

    op.alter_column(
        "users", "id", type_=UUID_TYPE, postgresql_using="id::uuid", existing_nullable=False
    )

    op.alter_column(
        "aquariums", "id", type_=UUID_TYPE, postgresql_using="id::uuid", existing_nullable=False
    )
    op.alter_column(
        "aquariums",
        "owner_user_id",
        type_=UUID_TYPE,
        postgresql_using="owner_user_id::uuid",
        existing_nullable=False,
    )

    op.alter_column(
        "aquarium_measurements",
        "id",
        type_=UUID_TYPE,
        postgresql_using="id::uuid",
        existing_nullable=False,
    )
    op.alter_column(
        "aquarium_measurements",
        "aquarium_id",
        type_=UUID_TYPE,
        postgresql_using="aquarium_id::uuid",
        existing_nullable=False,
    )

    op.alter_column(
        "aquarium_parameter_thresholds",
        "id",
        type_=UUID_TYPE,
        postgresql_using="id::uuid",
        existing_nullable=False,
    )
    op.alter_column(
        "aquarium_parameter_thresholds",
        "aquarium_id",
        type_=UUID_TYPE,
        postgresql_using="aquarium_id::uuid",
        existing_nullable=False,
    )

    op.alter_column(
        "parameters", "id", type_=UUID_TYPE, postgresql_using="id::uuid", existing_nullable=False
    )

    op.create_foreign_key(
        FK_AQUARIUMS_OWNER, "aquariums", "users", ["owner_user_id"], ["id"], ondelete="CASCADE"
    )
    op.create_foreign_key(
        FK_MEASUREMENTS_AQUARIUM,
        "aquarium_measurements",
        "aquariums",
        ["aquarium_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        FK_THRESHOLDS_AQUARIUM,
        "aquarium_parameter_thresholds",
        "aquariums",
        ["aquarium_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint(FK_THRESHOLDS_AQUARIUM, "aquarium_parameter_thresholds", type_="foreignkey")
    op.drop_constraint(FK_MEASUREMENTS_AQUARIUM, "aquarium_measurements", type_="foreignkey")
    op.drop_constraint(FK_AQUARIUMS_OWNER, "aquariums", type_="foreignkey")

    op.alter_column(
        "parameters", "id", type_=STRING_36, postgresql_using="id::text", existing_nullable=False
    )

    op.alter_column(
        "aquarium_parameter_thresholds",
        "aquarium_id",
        type_=STRING_36,
        postgresql_using="aquarium_id::text",
        existing_nullable=False,
    )
    op.alter_column(
        "aquarium_parameter_thresholds",
        "id",
        type_=STRING_36,
        postgresql_using="id::text",
        existing_nullable=False,
    )

    op.alter_column(
        "aquarium_measurements",
        "aquarium_id",
        type_=STRING_36,
        postgresql_using="aquarium_id::text",
        existing_nullable=False,
    )
    op.alter_column(
        "aquarium_measurements",
        "id",
        type_=STRING_36,
        postgresql_using="id::text",
        existing_nullable=False,
    )

    op.alter_column(
        "aquariums",
        "owner_user_id",
        type_=STRING_36,
        postgresql_using="owner_user_id::text",
        existing_nullable=False,
    )
    op.alter_column(
        "aquariums", "id", type_=STRING_36, postgresql_using="id::text", existing_nullable=False
    )

    op.alter_column(
        "users", "id", type_=STRING_36, postgresql_using="id::text", existing_nullable=False
    )

    op.create_foreign_key(
        FK_AQUARIUMS_OWNER, "aquariums", "users", ["owner_user_id"], ["id"], ondelete="CASCADE"
    )
    op.create_foreign_key(
        FK_MEASUREMENTS_AQUARIUM,
        "aquarium_measurements",
        "aquariums",
        ["aquarium_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        FK_THRESHOLDS_AQUARIUM,
        "aquarium_parameter_thresholds",
        "aquariums",
        ["aquarium_id"],
        ["id"],
        ondelete="CASCADE",
    )
