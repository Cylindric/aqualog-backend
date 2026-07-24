"""add_username_to_users

Revision ID: 87c03590a965
Revises: 20260719_000001
Create Date: 2026-07-24 18:20:18.036612
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "87c03590a965"
down_revision: Union[str, Sequence[str], None] = "20260719_000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("username", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "username")
