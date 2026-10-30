from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import Company, PortfolioMember


def list_portfolio(db: Session) -> list[PortfolioMember]:
    statement = select(PortfolioMember).options(joinedload(PortfolioMember.company)).order_by(PortfolioMember.id)
    return list(db.scalars(statement).unique())


def add_portfolio_member(db: Session, ticker: str, exchange: str) -> PortfolioMember:
    normalized_ticker = ticker.strip().upper()
    normalized_exchange = exchange.strip().upper()
    company = db.scalar(select(Company).where(Company.ticker == normalized_ticker, Company.exchange == normalized_exchange))
    if company is None:
        raise LookupError("Company not found")
    existing = db.scalar(select(PortfolioMember).where(PortfolioMember.company_id == company.id))
    if existing is not None:
        raise ValueError("Company is already in the portfolio")
    member = PortfolioMember(company=company)
    db.add(member)
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
    db.delete(member)
    db.commit()
