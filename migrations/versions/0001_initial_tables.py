"""initial tables

Revision ID: 0001
Revises:
Create Date: 2025-12-13

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("api_key", sa.String(length=96), nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=True),
        sa.Column("webhook_url", sa.String(length=2048), nullable=True),
        sa.Column(
            "branding_config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.create_index("ix_tenants_api_key", "tenants", ["api_key"], unique=True)
    op.create_index("ix_tenants_name", "tenants", ["name"], unique=False)

    op.create_table(
        "scripted_responses",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("trigger_keyword", sa.String(length=255), nullable=False),
        sa.Column("response_text", sa.Text(), nullable=False),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_scripted_responses_tenant_id",
        "scripted_responses",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_scripted_responses_tenant_trigger",
        "scripted_responses",
        ["tenant_id", "trigger_keyword"],
        unique=False,
    )
    op.create_index(
        "ix_scripted_responses_tenant_active",
        "scripted_responses",
        ["tenant_id", "is_active"],
        unique=False,
    )

    op.create_table(
        "leads",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("customer_name", sa.String(length=255), nullable=True),
        sa.Column("phone_number", sa.String(length=64), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_leads_tenant_id", "leads", ["tenant_id"], unique=False)
    op.create_index(
        "ix_leads_tenant_created_at", "leads", ["tenant_id", "created_at"], unique=False
    )
    op.create_index(
        "ix_leads_tenant_phone", "leads", ["tenant_id", "phone_number"], unique=False
    )

    op.create_table(
        "chat_logs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("lead_id", sa.BigInteger(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "sender_type", sa.Enum("user", "bot", name="sender_type"), nullable=False
        ),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_chat_logs_lead_id", "chat_logs", ["lead_id"], unique=False)
    op.create_index(
        "ix_chat_logs_lead_ts", "chat_logs", ["lead_id", "timestamp"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_chat_logs_lead_ts", table_name="chat_logs")
    op.drop_index("ix_chat_logs_lead_id", table_name="chat_logs")
    op.drop_table("chat_logs")

    op.drop_index("ix_leads_tenant_phone", table_name="leads")
    op.drop_index("ix_leads_tenant_created_at", table_name="leads")
    op.drop_index("ix_leads_tenant_id", table_name="leads")
    op.drop_table("leads")

    op.drop_index(
        "ix_scripted_responses_tenant_active", table_name="scripted_responses"
    )
    op.drop_index(
        "ix_scripted_responses_tenant_trigger", table_name="scripted_responses"
    )
    op.drop_index("ix_scripted_responses_tenant_id", table_name="scripted_responses")
    op.drop_table("scripted_responses")

    op.drop_index("ix_tenants_name", table_name="tenants")
    op.drop_index("ix_tenants_api_key", table_name="tenants")
    op.drop_table("tenants")

    # Enum type cleanup (Postgres)
    op.execute("DROP TYPE IF EXISTS sender_type")
