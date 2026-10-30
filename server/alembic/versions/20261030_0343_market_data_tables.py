"""Create market price and sync status tables.

Revision ID: 20261030_0343
Revises: 20261030_0328
"""
from alembic import op
import sqlalchemy as sa

revision = "20261030_0343"
down_revision = "20261030_0328"
branch_labels = None
dependencies = None


def upgrade() -> None:
    op.create_table(
        "market_prices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("price_date", sa.Date(), nullable=False),
        sa.Column("open", sa.Float(), nullable=True),
        sa.Column("high", sa.Float(), nullable=True),
        sa.Column("low", sa.Float(), nullable=True),
        sa.Column("close", sa.Float(), nullable=False),
        sa.Column("volume", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], name="fk_market_prices_company_id_companies", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_market_prices"),
        sa.UniqueConstraint("company_id", "price_date", name="uq_market_prices_company_date"),
    )
    op.create_index("ix_market_prices_company_id", "market_prices", ["company_id"], unique=False)
    op.create_index("ix_market_prices_price_date", "market_prices", ["price_date"], unique=False)
    op.create_table(
        "market_sync_status",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("records_updated", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_market_sync_status"),
    )


def downgrade() -> None:
    op.drop_table("market_sync_status")
    op.drop_index("ix_market_prices_price_date", table_name="market_prices")
    op.drop_index("ix_market_prices_company_id", table_name="market_prices")
    op.drop_table("market_prices")
