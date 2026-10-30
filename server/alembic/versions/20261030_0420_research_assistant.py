"""Add extracted document text for the research assistant.

Revision ID: 20261030_0420
Revises: 20261030_0410
"""
from alembic import op
import sqlalchemy as sa

revision = "20261030_0420"
down_revision = "20261030_0410"
branch_labels = None
dependencies = None


def upgrade() -> None:
    op.add_column("research_documents", sa.Column("extracted_text", sa.Text(), nullable=True))
    op.add_column("research_documents", sa.Column("content_status", sa.String(length=20), nullable=False, server_default="not_downloaded"))
    op.add_column("research_documents", sa.Column("extracted_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("research_documents", "extracted_at")
    op.drop_column("research_documents", "content_status")
    op.drop_column("research_documents", "extracted_text")
