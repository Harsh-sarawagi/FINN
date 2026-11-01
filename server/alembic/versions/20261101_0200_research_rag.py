"""Add semantic document chunks for research RAG.

Revision ID: 20261101_0200
Revises: 20261031_0119
"""
from alembic import op
import sqlalchemy as sa

revision = "20261101_0200"
down_revision = "20261031_0119"
branch_labels = None
dependencies = None


def upgrade() -> None:
    op.create_table(
        "research_document_chunks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("research_documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("section", sa.String(length=200), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", sa.Text(), nullable=True),
        sa.Column("embedding_model", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("document_id", "chunk_index", name="uq_research_document_chunk"),
    )
    op.create_index("ix_research_document_chunks_document_id", "research_document_chunks", ["document_id"])


def downgrade() -> None:
    op.drop_index("ix_research_document_chunks_document_id", table_name="research_document_chunks")
    op.drop_table("research_document_chunks")
