"""create aquariums table

Revision ID: 20260717_000001
Revises: 20260716_000001
Create Date: 2026-07-17 00:00:01
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260717_000001"
down_revision: Union[str, Sequence[str], None] = "20260716_000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "aquariums",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("owner_user_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("type", sa.String(length=24), nullable=False),
        sa.Column("volume_liters", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_user_id", "name", name="uq_aquariums_owner_name"),
    )
    op.create_index("ix_aquariums_owner_user_id", "aquariums", ["owner_user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_aquariums_owner_user_id", table_name="aquariums")
    op.drop_table("aquariums")
