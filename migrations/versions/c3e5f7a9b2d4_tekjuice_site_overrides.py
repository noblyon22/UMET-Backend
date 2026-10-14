"""Tek Juice site overrides (connector site.changes).

Revision ID: c3e5f7a9b2d4
Revises: b2d4e6f8a1c3
Create Date: 2026-10-14

The application also creates this table at startup when it is missing
(``tekjuice_s2s.ensure_content_columns``); this migration records it.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c3e5f7a9b2d4"
down_revision: Union[str, Sequence[str], None] = "b2d4e6f8a1c3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if "tekjuice_site_overrides" not in sa.inspect(op.get_bind()).get_table_names():
        op.create_table(
            "tekjuice_site_overrides",
            sa.Column("path", sa.String(length=300), primary_key=True),
            sa.Column("data", sa.Text(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True)),
        )


def downgrade() -> None:
    op.drop_table("tekjuice_site_overrides")
