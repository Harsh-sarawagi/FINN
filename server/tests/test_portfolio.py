from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.database.base import Base
from app.models import Company, PortfolioMember, PortfolioMemberHistory
from app.services.portfolio import add_portfolio_member, list_companies, list_portfolio, remove_portfolio_member


def portfolio_db() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_catalog_search_finds_unlisted_portfolio_companies() -> None:
    db = portfolio_db()
    db.add_all([
        Company(ticker="TCS", name="Tata Consultancy Services Limited", exchange="NSE"),
        Company(ticker="532540", name="Tata Consultancy Services Limited", exchange="BSE"),
    ])
    db.commit()

    assert [company.name for company in list_companies(db, "consultancy")] == [
        "Tata Consultancy Services Limited",
        "Tata Consultancy Services Limited",
    ]
    assert [company.ticker for company in list_companies(db, "532540")] == ["532540"]


def test_remove_reactivate_preserves_membership_and_history() -> None:
    db = portfolio_db()
    company = Company(ticker="TCS", name="Tata Consultancy Services Limited", exchange="NSE")
    db.add(company)
    db.commit()

    member = add_portfolio_member(db, "TCS", "NSE")
    member_id = member.id
    remove_portfolio_member(db, "TCS", "NSE")

    inactive = db.scalar(select(PortfolioMember).where(PortfolioMember.company_id == company.id))
    assert inactive is not None
    assert inactive.id == member_id
    assert inactive.is_active is False
    assert inactive.removed_at is not None
    assert db.scalar(select(Company).where(Company.id == company.id)) is not None

    restored = add_portfolio_member(db, "TCS", "NSE")
    assert restored.id == member_id
    assert restored.is_active is True
    assert restored.removed_at is None
    assert db.query(PortfolioMember).count() == 1

    history = db.scalars(select(PortfolioMemberHistory).order_by(PortfolioMemberHistory.id)).all()
    assert [item.action for item in history] == ["added", "removed", "added"]


def test_duplicate_active_member_is_rejected() -> None:
    db = portfolio_db()
    db.add(Company(ticker="INFY", name="Infosys Limited", exchange="NSE"))
    db.commit()
    add_portfolio_member(db, "INFY", "NSE")

    try:
        add_portfolio_member(db, "INFY", "NSE")
    except ValueError as exc:
        assert "already" in str(exc)
    else:
        raise AssertionError("Duplicate active portfolio membership was accepted")
