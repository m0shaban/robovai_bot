"""Add message_templates table

Revision ID: 0004
Revises: 0003
Create Date: 2024-12-14

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if table already exists (in case of partial migration)
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if "message_templates" in inspector.get_table_names():
        # Table already exists, skip
        return

    # Create template_category enum only if it doesn't exist
    # Using raw SQL for better control
    conn.execute(
        sa.text(
            """
        DO $$ BEGIN
            CREATE TYPE template_category AS ENUM (
                'welcome', 'farewell', 'complaint', 'inquiry', 'promotion',
                'support', 'payment', 'shipping', 'general'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """
        )
    )

    # Create message_templates table
    op.create_table(
        "message_templates",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "category",
            postgresql.ENUM(
                "welcome",
                "farewell",
                "complaint",
                "inquiry",
                "promotion",
                "support",
                "payment",
                "shipping",
                "general",
                name="template_category",
                create_type=False,
            ),
            nullable=False,
            server_default="general",
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("variables", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes
    op.create_index(
        "ix_message_templates_tenant_id", "message_templates", ["tenant_id"]
    )
    op.create_index(
        "ix_message_templates_tenant_category",
        "message_templates",
        ["tenant_id", "category"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_message_templates_tenant_category", table_name="message_templates"
    )
    op.drop_index("ix_message_templates_tenant_id", table_name="message_templates")
    op.drop_table("message_templates")

    # Drop the enum type
    op.execute("DROP TYPE IF EXISTS template_category")
