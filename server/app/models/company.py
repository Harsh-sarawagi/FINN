from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.portfolio_member import PortfolioMember


class Company(TimestampMixin, Base):
    __tablename__ = "companies"
    __table_args__ = (
        UniqueConstraint("exchange", "ticker", name="uq_companies_exchange_ticker"),
        CheckConstraint("length(trim(ticker)) > 0", name="companies_ticker_not_empty"),
        CheckConstraint("length(trim(name)) > 0", name="companies_name_not_empty"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    ticker: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    exchange: Mapped[str] = mapped_column(String(10), nullable=False, default="NSE")

    portfolio_members: Mapped[list["PortfolioMember"]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )
