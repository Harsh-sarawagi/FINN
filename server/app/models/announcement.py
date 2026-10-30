from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.company import Company


class Announcement(Base):
    __tablename__ = "announcements"
    __table_args__ = (
        UniqueConstraint("company_id", "source_url", "published_at", name="uq_announcements_company_source_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="other")
    source_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    source_name: Mapped[str] = mapped_column(String(50), nullable=False, default="NSE")
    published_at: Mapped[datetime] = mapped_column(nullable=False, index=True)
    ingested_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    ingestion_status: Mapped[str] = mapped_column(String(20), nullable=False, default="received")
    external_id: Mapped[str | None] = mapped_column(String(200))
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    summary: Mapped[str | None] = mapped_column(Text)
    ai_generated: Mapped[bool] = mapped_column(default=False, nullable=False)
    is_demo: Mapped[bool] = mapped_column(default=False, nullable=False)

    company: Mapped["Company"] = relationship()


class AnnouncementIngestionStatus(Base):
    __tablename__ = "announcement_ingestion_status"

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="NSE")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    last_attempt_at: Mapped[datetime | None] = mapped_column()
    last_success_at: Mapped[datetime | None] = mapped_column()
    records_added: Mapped[int] = mapped_column(default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(String(1000))
