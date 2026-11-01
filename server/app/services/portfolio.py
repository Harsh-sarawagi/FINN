from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload
from datetime import UTC, datetime
import logging
import re
import yfinance as yf

from app.models import Company, PortfolioMember
from app.models.portfolio_member import PortfolioMemberHistory

logger = logging.getLogger(__name__)


def list_portfolio(db: Session) -> list[PortfolioMember]:
    statement = select(PortfolioMember).options(joinedload(PortfolioMember.company)).where(PortfolioMember.is_active.is_(True)).order_by(PortfolioMember.id)
    return list(db.scalars(statement).unique())


def list_portfolio_history(db: Session) -> list[PortfolioMemberHistory]:
    return list(db.scalars(select(PortfolioMemberHistory).options(joinedload(PortfolioMemberHistory.company)).order_by(PortfolioMemberHistory.occurred_at.desc())).unique())


def list_companies(db: Session, query: str = "") -> list[Company]:
    statement = select(Company)
    if query.strip():
        normalized_query = query.strip()
        term = f"%{normalized_query}%"
        statement = statement.where(or_(Company.name.ilike(term), Company.ticker.ilike(term.upper())))
    return list(db.scalars(statement.order_by(Company.exchange, Company.ticker)).unique())


def add_portfolio_member(db: Session, ticker: str, exchange: str) -> PortfolioMember:
    normalized_ticker = ticker.strip().upper()
    normalized_exchange = exchange.strip().upper()
    if normalized_exchange not in {"NSE", "BSE"}:
        raise ValueError("Exchange must be NSE or BSE")
    company = db.scalar(select(Company).where(Company.ticker == normalized_ticker, Company.exchange == normalized_exchange))
    if company is None:
        raise LookupError("Company not found")
    existing = db.scalar(select(PortfolioMember).where(PortfolioMember.company_id == company.id))
    if existing is not None and existing.is_active:
        raise ValueError("Company is already in the portfolio")
    if existing is None:
        member = PortfolioMember(company=company, is_active=True, previous_status="active")
        db.add(member)
        db.flush()
    else:
        member = existing
        member.is_active = True
        member.removed_at = None
        member.previous_status = "active"
        now = datetime.now(UTC)
        member.added_at = now
        member.updated_at = now
    db.add(PortfolioMemberHistory(company_id=company.id, action="added", previous_status="active" if existing and not existing.is_active else "never_active"))
    db.commit()
    db.refresh(member)
    return member


def remove_portfolio_member(db: Session, ticker: str, exchange: str) -> None:
    company = db.scalar(select(Company).where(Company.ticker == ticker.strip().upper(), Company.exchange == exchange.strip().upper()))
    if company is None:
        raise LookupError("Company not found")
    member = db.scalar(select(PortfolioMember).where(PortfolioMember.company_id == company.id))
    if member is None:
        raise LookupError("Portfolio member not found")
    if not member.is_active:
        raise ValueError("Company is already removed from the portfolio")
    member.previous_status = "active"
    member.is_active = False
    now = datetime.now(UTC)
    member.removed_at = now
    member.updated_at = now
    db.add(PortfolioMemberHistory(company_id=company.id, action="removed", previous_status="active"))
    db.commit()


def discover_company(db: Session, ticker: str, exchange: str, name: str | None = None) -> Company:
    normalized_ticker = re.sub(r"\s+", "", ticker.strip().upper())
    normalized_exchange = exchange.strip().upper()
    if normalized_exchange not in {"NSE", "BSE"}:
        raise ValueError("Exchange must be NSE or BSE")
    if not re.fullmatch(r"[A-Z0-9&._-]{1,20}", normalized_ticker):
        raise ValueError("Invalid exchange symbol")
    existing = db.scalar(select(Company).where(Company.exchange == normalized_exchange, Company.ticker == normalized_ticker))
    if existing:
        return existing
    resolved_name = name.strip() if name and name.strip() else None
    if resolved_name is None:
        suffix = "NS" if normalized_exchange == "NSE" else "BO"
        try:
            info = yf.Ticker(f"{normalized_ticker}.{suffix}").get_info()
            resolved_name = str(info.get("longName") or info.get("shortName") or "").strip() or None
        except Exception as exc:
            logger.warning("Company discovery failed for %s.%s: %s", normalized_ticker, normalized_exchange, exc)
    if not resolved_name:
        raise LookupError("Company could not be verified by the provider")
    company = Company(ticker=normalized_ticker, name=resolved_name, exchange=normalized_exchange)
    db.add(company)
    db.commit()
    db.refresh(company)
    return company
