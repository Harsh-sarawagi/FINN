"""Add announcement and push intelligence tables.

Revision ID: 20261030_0400
Revises: 20261030_0343
"""
from alembic import op
import sqlalchemy as sa

revision = "20261030_0400"
down_revision = "20261030_0343"
branch_labels = None
dependencies = None


def upgrade() -> None:
    op.create_table(
        "announcements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=50), nullable=False, server_default="other"),
        sa.Column("source_url", sa.String(length=1000), nullable=False),
        sa.Column("source_name", sa.String(length=50), nullable=False, server_default="NSE"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("ingestion_status", sa.String(length=20), nullable=False, server_default="received"),
        sa.Column("external_id", sa.String(length=200), nullable=True),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("ai_generated", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "source_url", "published_at", name="uq_announcements_company_source_date"),
    )
    op.create_index("ix_announcements_company_id", "announcements", ["company_id"])
    op.create_index("ix_announcements_published_at", "announcements", ["published_at"])
    op.create_index("ix_announcements_fingerprint", "announcements", ["fingerprint"])

    op.create_table(
        "announcement_ingestion_status",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False, server_default="NSE"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("records_added", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.String(length=1000), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "alert_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=True),
        sa.Column("company_id", sa.Integer(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alert_rules_company_id", "alert_rules", ["company_id"])
    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("rule_id", sa.Integer(), nullable=False),
        sa.Column("announcement_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["rule_id"], ["alert_rules.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["announcement_id"], ["announcements.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("rule_id", "announcement_id", name="uq_alert_rule_announcement"),
    )
    op.create_index("ix_alerts_rule_id", "alerts", ["rule_id"])
    op.create_index("ix_alerts_announcement_id", "alerts", ["announcement_id"])


def downgrade() -> None:
    op.drop_index("ix_alerts_announcement_id", table_name="alerts")
    op.drop_index("ix_alerts_rule_id", table_name="alerts")
    op.drop_table("alerts")
    op.drop_index("ix_alert_rules_company_id", table_name="alert_rules")
    op.drop_table("alert_rules")
    op.drop_table("announcement_ingestion_status")
    op.drop_index("ix_announcements_fingerprint", table_name="announcements")
    op.drop_index("ix_announcements_published_at", table_name="announcements")
    op.drop_index("ix_announcements_company_id", table_name="announcements")
    op.drop_table("announcements")
