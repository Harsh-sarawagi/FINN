"""Create company and portfolio member tables.

Revision ID: 20261030_0328
Revises:
Create Date: 2026-10-30
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261030_0328"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
dependencies: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "companies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ticker", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("exchange", sa.String(length=10), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("length(trim(ticker)) > 0", name="ck_companies_companies_ticker_not_empty"),
        sa.CheckConstraint("length(trim(name)) > 0", name="ck_companies_companies_name_not_empty"),
        sa.PrimaryKeyConstraint("id", name="pk_companies"),
        sa.UniqueConstraint("exchange", "ticker", name="uq_companies_exchange_ticker"),
    )
    op.create_table(
        "portfolio_members",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("added_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], name="fk_portfolio_members_company_id_companies", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_portfolio_members"),
        sa.UniqueConstraint("company_id", name="uq_portfolio_members_company_id"),
    )


def downgrade() -> None:
    op.drop_table("portfolio_members")
    op.drop_table("companies")
