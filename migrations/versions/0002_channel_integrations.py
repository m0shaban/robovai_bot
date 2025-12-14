"""add channel_integrations

Revision ID: 0002
Revises: 0001
Create Date: 2025-12-13

"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "channel_integrations",
        sa.Column(
            "id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False
        ),
        sa.Column(
            "tenant_id",
            sa.BigInteger(),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("channel_type", sa.String(length=32), nullable=False),
        sa.Column("external_id", sa.String(length=128), nullable=True),
        sa.Column("access_token", sa.Text(), nullable=True),
        sa.Column("verify_token", sa.String(length=128), nullable=False),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "channel_type", "external_id", name="uq_channel_type_external_id"
        ),
    )

    op.create_index(
        "ix_channel_integrations_tenant_id", "channel_integrations", ["tenant_id"]
    )
    op.create_index(
        "ix_channel_integrations_channel_type", "channel_integrations", ["channel_type"]
    )
    op.create_index(
        "ix_channel_integrations_verify_token", "channel_integrations", ["verify_token"]
    )
    op.create_index(
        "ix_channel_integrations_tenant_type",
        "channel_integrations",
        ["tenant_id", "channel_type"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_channel_integrations_tenant_type", table_name="channel_integrations"
    )
    op.drop_index(
        "ix_channel_integrations_verify_token", table_name="channel_integrations"
    )
    op.drop_index(
        "ix_channel_integrations_channel_type", table_name="channel_integrations"
    )
    op.drop_index(
        "ix_channel_integrations_tenant_id", table_name="channel_integrations"
    )
    op.drop_table("channel_integrations")
