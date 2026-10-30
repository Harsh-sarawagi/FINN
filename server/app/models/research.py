from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, Float, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.company import Company


class FinancialResult(Base):
    __tablename__ = "financial_results"
    __table_args__ = (UniqueConstraint("company_id", "period_end", "basis", "metric", name="uq_financial_result"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    period_end: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    period_label: Mapped[str] = mapped_column(String(30), nullable=False)
    basis: Mapped[str] = mapped_column(String(20), nullable=False, default="consolidated")
    metric: Mapped[str] = mapped_column(String(30), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(30), nullable=False, default="currency units")
    source_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    source_name: Mapped[str] = mapped_column(String(50), nullable=False, default="yfinance")
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    is_derived: Mapped[bool] = mapped_column(default=False, nullable=False)


class ResearchDocument(Base):
    __tablename__ = "research_documents"
    __table_args__ = (UniqueConstraint("company_id", "source_url", name="uq_research_document_source"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    document_type: Mapped[str] = mapped_column(String(50), nullable=False, default="other")
    source_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    source_name: Mapped[str] = mapped_column(String(50), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    period_label: Mapped[str | None] = mapped_column(String(30))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    extracted_text: Mapped[str | None] = mapped_column(Text)
    content_status: Mapped[str] = mapped_column(String(20), nullable=False, default="not_downloaded")
    extracted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ManagementGuidance(Base):
    __tablename__ = "management_guidance"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    period_label: Mapped[str | None] = mapped_column(String(30))
    source_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    source_name: Mapped[str] = mapped_column(String(50), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    extracted: Mapped[bool] = mapped_column(default=False, nullable=False)
