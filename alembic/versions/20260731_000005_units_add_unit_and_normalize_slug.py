"""units_add_unit_and_normalize_slug

Revision ID: 20260731_000005
Revises: 20260731_000004
Create Date: 2026-07-31 00:00:05
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260731_000005"
down_revision: Union[str, Sequence[str], None] = "20260731_000004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

IX_UNITS_SLUG_LOWER = "ix_units_slug_lower"
IX_UNITS_SLUG = "ix_units_slug"


def upgrade() -> None:
    # `unit` carries the original notation (e.g. "mg/L", "pH"); `slug` becomes a
    # URL-safe routing key (lowercase, "/" -> "_") — it can no longer double as the
    # notation once it must be safe as a single path segment.
    op.add_column("units", sa.Column("unit", sa.String(length=16), nullable=True))
    op.execute("UPDATE units SET unit = slug")
    op.alter_column("units", "unit", nullable=False)

    op.execute("UPDATE units SET slug = lower(replace(slug, '/', '_'))")
    op.execute("UPDATE units SET unit = 'US Gal' WHERE unit = 'gal_us'")
    op.execute("UPDATE units SET unit = 'SG' WHERE unit = 'sg'")
    op.execute("UPDATE units SET unit = '°C' WHERE unit = 'celsius'")
    op.execute("UPDATE units SET unit = '°F' WHERE unit = 'fahrenheit'")

    op.drop_index(IX_UNITS_SLUG_LOWER, table_name="units")
    op.create_index(IX_UNITS_SLUG, "units", ["slug"], unique=True)


def downgrade() -> None:
    op.drop_index(IX_UNITS_SLUG, table_name="units")
    op.execute("UPDATE units SET slug = unit")
    op.create_index(IX_UNITS_SLUG_LOWER, "units", [sa.text("lower(slug)")], unique=True)

    op.drop_column("units", "unit")
