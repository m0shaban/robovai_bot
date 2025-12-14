"""add quick_replies

Revision ID: 0003
Revises: 0002
Create Date: 2025-12-13

"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op


revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "quick_replies",
        sa.Column(
            "id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False
        ),
        sa.Column(
            "tenant_id",
            sa.BigInteger(),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=64), nullable=False),
        sa.Column("payload_text", sa.String(length=512), nullable=False),
        sa.Column(
            "sort_order",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_index("ix_quick_replies_tenant_id", "quick_replies", ["tenant_id"])
    op.create_index(
        "ix_quick_replies_tenant_active",
        "quick_replies",
        ["tenant_id", "is_active"],
    )
    op.create_index(
        "ix_quick_replies_tenant_order",
        "quick_replies",
        ["tenant_id", "sort_order", "id"],
    )


def downgrade() -> None:
    op.drop_index("ix_quick_replies_tenant_order", table_name="quick_replies")
    op.drop_index("ix_quick_replies_tenant_active", table_name="quick_replies")
    op.drop_index("ix_quick_replies_tenant_id", table_name="quick_replies")
    op.drop_table("quick_replies")
