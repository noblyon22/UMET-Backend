"""Add Tek Juice Data Engine publication ledger.

Revision ID: 9f3b7c1d2a44
Revises: 7ea8b1c253ae
Create Date: 2026-09-28
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9f3b7c1d2a44"
down_revision: Union[str, Sequence[str], None] = "7ea8b1c253ae"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tekjuice_publications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("execution_id", sa.String(length=255), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("website_id", sa.String(length=255), nullable=False),
        sa.Column("action_type", sa.String(length=50), nullable=False),
        sa.Column("resource_id", sa.Integer(), nullable=True),
        sa.Column("published_url", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "execution_id",
            name="uq_tekjuice_publications_execution_id",
        ),
        sa.UniqueConstraint(
            "idempotency_key",
            name="uq_tekjuice_publications_idempotency_key",
        ),
    )

    op.create_index(
        "ix_tekjuice_publications_execution_id",
        "tekjuice_publications",
        ["execution_id"],
        unique=False,
    )
    op.create_index(
        "ix_tekjuice_publications_idempotency_key",
        "tekjuice_publications",
        ["idempotency_key"],
        unique=False,
    )
    op.create_index(
        "ix_tekjuice_publications_website_id",
        "tekjuice_publications",
        ["website_id"],
        unique=False,
    )
    op.create_index(
        "ix_tekjuice_publications_status",
        "tekjuice_publications",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_tekjuice_publications_status",
        table_name="tekjuice_publications",
    )
    op.drop_index(
        "ix_tekjuice_publications_website_id",
        table_name="tekjuice_publications",
    )
    op.drop_index(
        "ix_tekjuice_publications_idempotency_key",
        table_name="tekjuice_publications",
    )
    op.drop_index(
        "ix_tekjuice_publications_execution_id",
        table_name="tekjuice_publications",
    )
    op.drop_table("tekjuice_publications")
