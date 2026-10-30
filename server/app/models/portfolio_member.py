from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.company import Company


class PortfolioMember(Base):
    __tablename__ = "portfolio_members"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    added_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

    company: Mapped["Company"] = relationship(back_populates="portfolio_members")
