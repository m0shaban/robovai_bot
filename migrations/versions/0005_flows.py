"""add flows and update leads

Revision ID: 0004
Revises: 0003
Create Date: 2025-12-14

"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op


revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create flows table
    op.create_table(
        "flows",
        sa.Column(
            "id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False
        ),
        sa.Column(
            "tenant_id",
            sa.BigInteger(),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("trigger_keyword", sa.String(length=255), nullable=True),
        sa.Column(
            "flow_data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
    )
    op.create_index(
        "ix_flows_tenant_trigger", "flows", ["tenant_id", "trigger_keyword"]
    )

    # Update leads table
    op.add_column(
        "leads",
        sa.Column(
            "current_flow_id",
            sa.BigInteger(),
            sa.ForeignKey("flows.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "leads", sa.Column("current_step_id", sa.String(length=255), nullable=True)
    )
    op.add_column(
        "leads",
        sa.Column(
            "flow_context",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("leads", "flow_context")
    op.drop_column("leads", "current_step_id")
    op.drop_column("leads", "current_flow_id")
    op.drop_table("flows")
