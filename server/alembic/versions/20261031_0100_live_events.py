"""Add PostgreSQL-backed dashboard event outbox.

Revision ID: 20261031_0100
Revises: 20261030_0420
"""
from alembic import op
import sqlalchemy as sa

revision = "20261031_0100"
down_revision = "20261030_0420"
branch_labels = None
dependencies = None


def upgrade() -> None:
    op.create_table(
        "event_outbox",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_event_outbox_event_type", "event_outbox", ["event_type"])
    op.create_index("ix_event_outbox_created_at", "event_outbox", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_event_outbox_created_at", table_name="event_outbox")
    op.drop_index("ix_event_outbox_event_type", table_name="event_outbox")
    op.drop_table("event_outbox")
