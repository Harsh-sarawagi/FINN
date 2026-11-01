"""Preserve portfolio lifecycle and removal history.

Revision ID: 20261031_0119
Revises: 20261031_0100
"""
from alembic import op
import sqlalchemy as sa

revision = "20261031_0119"
down_revision = "20261031_0100"
branch_labels = None
dependencies = None


def upgrade() -> None:
    op.add_column("portfolio_members", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("portfolio_members", sa.Column("removed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("portfolio_members", sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False))
    op.add_column("portfolio_members", sa.Column("previous_status", sa.String(length=20), nullable=False, server_default="active"))
    op.create_table(
        "portfolio_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=20), nullable=False),
        sa.Column("previous_status", sa.String(length=20), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_portfolio_history_company_id", "portfolio_history", ["company_id"])
    op.create_index("ix_portfolio_history_occurred_at", "portfolio_history", ["occurred_at"])
    portfolio_members = sa.table(
        "portfolio_members",
        sa.column("company_id", sa.Integer()),
        sa.column("added_at", sa.DateTime(timezone=True)),
        sa.column("previous_status", sa.String()),
    )
    portfolio_history = sa.table(
        "portfolio_history",
        sa.column("company_id", sa.Integer()),
        sa.column("action", sa.String()),
        sa.column("previous_status", sa.String()),
        sa.column("occurred_at", sa.DateTime(timezone=True)),
    )
    connection = op.get_bind()
    members = connection.execute(
        sa.select(portfolio_members.c.company_id, portfolio_members.c.added_at)
    ).all()
    if members:
        connection.execute(
            portfolio_history.insert(),
            [
                {
                    "company_id": company_id,
                    "action": "added",
                    "previous_status": "never_active",
                    "occurred_at": added_at,
                }
                for company_id, added_at in members
            ],
        )


def downgrade() -> None:
    op.drop_index("ix_portfolio_history_occurred_at", table_name="portfolio_history")
    op.drop_index("ix_portfolio_history_company_id", table_name="portfolio_history")
    op.drop_table("portfolio_history")
    op.drop_column("portfolio_members", "previous_status")
    op.drop_column("portfolio_members", "updated_at")
    op.drop_column("portfolio_members", "removed_at")
    op.drop_column("portfolio_members", "is_active")
