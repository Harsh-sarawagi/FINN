import logging
from datetime import UTC, datetime, timedelta

import pandas as pd
import yfinance as yf
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import Company, MarketPrice, MarketSyncStatus, PortfolioMember
from app.services.events import publish_event

logger = logging.getLogger(__name__)


def yahoo_symbol(company: Company) -> str:
    suffix = "NS" if company.exchange.upper() == "NSE" else "BO"
    return f"{company.ticker}.{suffix}"


def sync_portfolio_market_data(db: Session) -> MarketSyncStatus:
    status = db.scalar(select(MarketSyncStatus).order_by(MarketSyncStatus.id.desc()))
    if status is None:
        status = MarketSyncStatus(provider="yfinance")
        db.add(status)
        db.flush()

    status.status = "running"
    status.last_attempt_at = datetime.now(UTC)
    status.error_message = None
    db.commit()

    companies = db.scalars(
        select(Company).join(PortfolioMember, PortfolioMember.company_id == Company.id).where(PortfolioMember.is_active.is_(True))
    ).unique().all()
    records = 0

    try:
        for company in companies:
            try:
                history = yf.Ticker(yahoo_symbol(company)).history(period="10d", auto_adjust=False)
                if history.empty:
                    logger.warning("No market data returned for %s", company.ticker)
                    continue
                history = history.tail(5).dropna(subset=["Close"])
                for price_date, row in history.iterrows():
                    day = price_date.date()
                    existing = db.scalar(select(MarketPrice).where(
                        MarketPrice.company_id == company.id,
                        MarketPrice.price_date == day,
                    ))
                    volume_value = row.get("Volume")
                    volume = int(volume_value) if pd.notna(volume_value) else None
                    values = {
                        "open": float(row["Open"]) if pd.notna(row.get("Open")) else None,
                        "high": float(row["High"]) if pd.notna(row.get("High")) else None,
                        "low": float(row["Low"]) if pd.notna(row.get("Low")) else None,
                        "close": float(row["Close"]),
                        "volume": volume,
                        "source": "yfinance",
                        "fetched_at": datetime.now(UTC),
                    }
                    if existing:
                        for key, value in values.items():
                            setattr(existing, key, value)
                    else:
                        db.add(MarketPrice(company_id=company.id, price_date=day, **values))
                    records += 1
            except Exception as exc:
                logger.warning("Market data failed for %s: %s", company.ticker, exc)
        db.commit()
        final_status = "ok" if records else "partial"
        final_success_at = datetime.now(UTC) if records else status.last_success_at
        status.status = final_status
        status.last_success_at = final_success_at
        status.records_updated = records
        status.error_message = None if records else "No market records were returned by the provider"
        db.execute(
            update(MarketSyncStatus)
            .where(MarketSyncStatus.id == status.id)
            .values(
                status=final_status,
                last_success_at=final_success_at,
                records_updated=records,
                error_message=status.error_message,
            )
        )
        db.commit()
        if records:
            publish_event(db, "market.updated", {"records_updated": records})
    except Exception as exc:
        db.rollback()
        status.status = "failed"
        status.last_attempt_at = datetime.now(UTC)
        status.error_message = str(exc)[:500]
        db.commit()
    return status


def get_dashboard(db: Session) -> dict:
    members = db.scalars(select(PortfolioMember).where(PortfolioMember.is_active.is_(True)).order_by(PortfolioMember.id)).unique().all()
    instruments = []
    movers = []

    for member in members:
        company = db.get(Company, member.company_id)
        if not company:
            continue
        rows = db.scalars(select(MarketPrice).where(MarketPrice.company_id == company.id).order_by(MarketPrice.price_date.desc()).limit(20)).all()
        current = rows[0] if rows else None
        previous = rows[1] if len(rows) > 1 else None
        change = ((current.close / previous.close) - 1) * 100 if current and previous and previous.close else None
        price = current.close if current else None
        date_value = current.price_date.isoformat() if current else None
        history = [
            {"price_date": row.price_date.isoformat(), "close": round(row.close, 2)}
            for row in reversed(rows)
            if row.close is not None
        ]
        instruments.append({"ticker": company.ticker, "name": company.name, "exchange": company.exchange, "price": price, "change_percent": change, "volume": current.volume if current else None, "price_date": date_value, "history": history})
        if change is not None and price is not None:
            movers.append({"ticker": company.ticker, "name": company.name, "change_percent": round(change, 2), "price": round(price, 2)})

    changes = [item["change_percent"] for item in movers]
    gainers = sorted(movers, key=lambda item: item["change_percent"], reverse=True)
    losers = sorted(movers, key=lambda item: item["change_percent"])
    status = db.scalar(select(MarketSyncStatus).order_by(MarketSyncStatus.id.desc()))
    live = bool(members and len([item for item in instruments if item["price"] is not None]) > 0)

    return {
        "live_data": live,
        "is_demo_data": not live,
        "source": "Yahoo Finance / yfinance" if live else "No live market data",
        "last_updated": status.last_success_at if status and status.last_success_at else None,
        "portfolio_count": len(members),
        "portfolio_average_change": round(sum(changes) / len(changes), 2) if changes else None,
        "advancing_count": len([change for change in changes if change > 0]),
        "declining_count": len([change for change in changes if change < 0]),
        "instruments": instruments,
        "top_gainers": gainers[:3],
        "top_losers": losers[:3],
    }
