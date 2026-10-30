"""Add pull research financial and document tables.

Revision ID: 20261030_0410
Revises: 20261030_0400
"""
from alembic import op
import sqlalchemy as sa

revision = "20261030_0410"
down_revision = "20261030_0400"
branch_labels = None
dependencies = None


def upgrade() -> None:
    op.create_table("financial_results", sa.Column("id", sa.Integer(), nullable=False), sa.Column("company_id", sa.Integer(), nullable=False), sa.Column("period_end", sa.Date(), nullable=False), sa.Column("period_label", sa.String(30), nullable=False), sa.Column("basis", sa.String(20), nullable=False, server_default="consolidated"), sa.Column("metric", sa.String(30), nullable=False), sa.Column("value", sa.Float(), nullable=False), sa.Column("unit", sa.String(30), nullable=False, server_default="currency units"), sa.Column("source_url", sa.String(1000), nullable=False), sa.Column("source_name", sa.String(50), nullable=False, server_default="yfinance"), sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.Column("is_derived", sa.Boolean(), nullable=False, server_default=sa.text("false")), sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("company_id", "period_end", "basis", "metric", name="uq_financial_result"))
    op.create_index("ix_financial_results_company_id", "financial_results", ["company_id"])
    op.create_index("ix_financial_results_period_end", "financial_results", ["period_end"])
    op.create_table("research_documents", sa.Column("id", sa.Integer(), nullable=False), sa.Column("company_id", sa.Integer(), nullable=False), sa.Column("title", sa.String(500), nullable=False), sa.Column("document_type", sa.String(50), nullable=False, server_default="other"), sa.Column("source_url", sa.String(1000), nullable=False), sa.Column("source_name", sa.String(50), nullable=False), sa.Column("published_at", sa.DateTime(timezone=True), nullable=True), sa.Column("period_label", sa.String(30), nullable=True), sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("company_id", "source_url", name="uq_research_document_source"))
    op.create_index("ix_research_documents_company_id", "research_documents", ["company_id"])
    op.create_table("management_guidance", sa.Column("id", sa.Integer(), nullable=False), sa.Column("company_id", sa.Integer(), nullable=False), sa.Column("statement", sa.Text(), nullable=False), sa.Column("period_label", sa.String(30), nullable=True), sa.Column("source_url", sa.String(1000), nullable=False), sa.Column("source_name", sa.String(50), nullable=False), sa.Column("published_at", sa.DateTime(timezone=True), nullable=True), sa.Column("extracted", sa.Boolean(), nullable=False, server_default=sa.text("false")), sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_management_guidance_company_id", "management_guidance", ["company_id"])


def downgrade() -> None:
    op.drop_index("ix_management_guidance_company_id", table_name="management_guidance")
    op.drop_table("management_guidance")
    op.drop_index("ix_research_documents_company_id", table_name="research_documents")
    op.drop_table("research_documents")
    op.drop_index("ix_financial_results_period_end", table_name="financial_results")
    op.drop_index("ix_financial_results_company_id", table_name="financial_results")
    op.drop_table("financial_results")
