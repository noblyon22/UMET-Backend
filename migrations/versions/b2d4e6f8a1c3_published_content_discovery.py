"""Store Tek Juice GEO/AEO material with published content.

Revision ID: b2d4e6f8a1c3
Revises: 9f3b7c1d2a44
Create Date: 2026-10-14

The application also adds this column at startup when it is missing
(``tekjuice_s2s.ensure_content_columns``); this migration records it.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b2d4e6f8a1c3"
down_revision: Union[str, Sequence[str], None] = "9f3b7c1d2a44"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("published_content")}
    if "discovery" not in columns:
        op.add_column("published_content", sa.Column("discovery", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("published_content", "discovery")
