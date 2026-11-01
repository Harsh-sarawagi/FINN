import logging
from datetime import UTC, datetime
from typing import Iterable

import pandas as pd
import yfinance as yf
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Announcement, Company, FinancialResult, ManagementGuidance, ResearchDocument
from app.services.research_analytics import financial_analytics, market_analytics

logger = logging.getLogger(__name__)
METRIC_FIELDS = {
    "revenue": ("Total Revenue", "Revenue", "Sales"),
    "ebitda": ("EBITDA", "Normalized EBITDA"),
    "pbt": ("Pretax Income", "Pre Tax Income", "Profit Before Tax"),
    "pat": ("Net Income", "Net Income Common Stockholders", "Profit After Tax"),
}
EXTRA_METRIC_FIELDS = {
    "total_debt": ("Total Debt", "Long Term Debt", "Short Long Term Debt"),
    "total_equity": ("Stockholders Equity", "Total Equity Gross Minority Interest", "Total Stockholder Equity"),
    "cash_and_equivalents": ("Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments"),
    "operating_cash_flow": ("Operating Cash Flow", "Total Cash From Operating Activities"),
    "free_cash_flow": ("Free Cash Flow",),
    "current_assets": ("Current Assets",),
    "current_liabilities": ("Current Liabilities",),
}


def yahoo_symbol(ticker: str, exchange: str) -> str:
    return f"{ticker.strip().upper()}.{ 'NS' if exchange.upper() == 'NSE' else 'BO'}"


def resolve_company(db: Session, ticker: str, exchange: str = "NSE") -> Company:
    ticker = ticker.strip().upper()
    exchange = exchange.strip().upper()
    company = db.scalar(select(Company).where(Company.ticker == ticker, Company.exchange == exchange))
    if company:
        return company
    info = {}
    try:
        info = yf.Ticker(yahoo_symbol(ticker, exchange)).get_info()
    except Exception as exc:
        logger.warning("Unable to resolve %s: %s", ticker, exc)
        raise LookupError(f"Company/provider data unavailable for {exchange}:{ticker}") from exc
    name = str(info.get("longName") or info.get("shortName") or ticker).strip()
    if not name:
        raise LookupError(f"Company/provider data unavailable for {exchange}:{ticker}")
    company = Company(ticker=ticker, exchange=exchange, name=name)
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


def percentage_change(current: float, prior: float | None) -> float | None:
    if prior is None or prior == 0:
        return None
    return round(((current - prior) / abs(prior)) * 100, 2)


def sync_research(db: Session, ticker: str, exchange: str = "NSE") -> dict:
    company = resolve_company(db, ticker, exchange)
    source_url = f"https://finance.yahoo.com/quote/{yahoo_symbol(ticker, exchange)}"
    provider_error = None
    try:
        stock = yf.Ticker(yahoo_symbol(ticker, exchange))
        frame = stock.quarterly_income_stmt
        if frame is None or frame.empty:
            frame = stock.quarterly_financials
        period_count = 0
        if frame is not None and not frame.empty:
            for period in list(frame.columns)[:8]:
                period_end = pd.Timestamp(period).date()
                for metric, candidate_names in METRIC_FIELDS.items():
                    value = None
                    for candidate in candidate_names:
                        if candidate in frame.index:
                            raw = frame.loc[candidate, period]
                            if pd.notna(raw):
                                value = float(raw)
                                break
                    if value is None:
                        continue
                    existing = db.scalar(select(FinancialResult).where(FinancialResult.company_id == company.id, FinancialResult.period_end == period_end, FinancialResult.basis == "consolidated", FinancialResult.metric == metric))
                    if existing:
                        existing.value = value
                        existing.source_url = source_url
                        existing.fetched_at = datetime.now(UTC)
                    else:
                        db.add(FinancialResult(company_id=company.id, period_end=period_end, period_label=f"Q{((period_end.month - 1) // 3) + 1} {period_end.year}", basis="consolidated", metric=metric, value=value, unit="provider units", source_url=source_url, source_name="yfinance"))
                    period_count += 1
        balance_sheet = stock.quarterly_balance_sheet
        cash_flow = stock.quarterly_cashflow
        provider_frames = [
            (balance_sheet, ("total_debt", "total_equity", "cash_and_equivalents", "current_assets", "current_liabilities")),
            (cash_flow, ("operating_cash_flow", "free_cash_flow")),
        ]
        for frame, allowed_metrics in provider_frames:
            if frame is None or frame.empty:
                continue
            for period in list(frame.columns)[:8]:
                period_end = pd.Timestamp(period).date()
                for metric, candidates in EXTRA_METRIC_FIELDS.items():
                    if metric not in allowed_metrics:
                        continue
                    value = next((float(frame.loc[candidate, period]) for candidate in candidates if candidate in frame.index and pd.notna(frame.loc[candidate, period])), None)
                    if value is None:
                        continue
                    existing = db.scalar(select(FinancialResult).where(FinancialResult.company_id == company.id, FinancialResult.period_end == period_end, FinancialResult.basis == "consolidated", FinancialResult.metric == metric))
                    if existing:
                        existing.value = value
                        existing.fetched_at = datetime.now(UTC)
                    else:
                        db.add(FinancialResult(company_id=company.id, period_end=period_end, period_label=f"Q{((period_end.month - 1) // 3) + 1} {period_end.year}", basis="consolidated", metric=metric, value=value, unit="provider units", source_url=source_url, source_name="yfinance"))
        db.commit()
        sync_announcements_to_documents(db, company)
    except Exception as exc:
        provider_error = str(exc)[:500]
        logger.warning("Research sync failed for %s: %s", ticker, exc)
    return research_payload(db, company, provider_error)


def sync_announcements_to_documents(db: Session, company: Company) -> None:
    keywords = {
        "annual_report": ("annual report", "annual return", "integrated report"),
        "investor_presentation": ("investor presentation", "earnings presentation", "result presentation"),
        "quarterly_results": ("financial results", "quarterly results", "unaudited results"),
        "earnings_transcript": ("earnings transcript", "concall transcript", "conference call transcript"),
    }
    announcements = db.scalars(select(Announcement).where(Announcement.company_id == company.id)).all()
    for announcement in announcements:
        text = f"{announcement.title} {announcement.content or ''}".lower()
        kind = next((kind for kind, terms in keywords.items() if any(term in text for term in terms)), None)
        if not kind:
            continue
        if db.scalar(select(ResearchDocument.id).where(ResearchDocument.company_id == company.id, ResearchDocument.source_url == announcement.source_url)):
            continue
        db.add(ResearchDocument(company_id=company.id, title=announcement.title, document_type=kind, source_url=announcement.source_url, source_name=announcement.source_name, published_at=announcement.published_at, period_label=None))
    db.commit()


def research_payload(db: Session, company: Company, provider_error: str | None = None) -> dict:
    results = db.scalars(select(FinancialResult).where(FinancialResult.company_id == company.id).order_by(FinancialResult.period_end.desc(), FinancialResult.metric)).all()
    periods = []
    for period_end in sorted({result.period_end for result in results}, reverse=True):
        period_results = [result for result in results if result.period_end == period_end]
        metric_values = {result.metric: result.value for result in period_results}
        periods.append({
            "period_end": period_end,
            "period_label": period_results[0].period_label,
            "basis": period_results[0].basis,
            "unit": period_results[0].unit,
            "values": metric_values,
        })
    by_metric: dict[str, list[FinancialResult]] = {metric: [result for result in results if result.metric == metric] for metric in METRIC_FIELDS}
    comparisons = []
    for metric, metric_results in by_metric.items():
        ordered = sorted(metric_results, key=lambda result: result.period_end, reverse=True)
        if ordered:
            current = ordered[0]
            qoq = percentage_change(current.value, ordered[1].value if len(ordered) > 1 else None)
            yoy = percentage_change(current.value, ordered[4].value if len(ordered) > 4 else None)
            comparisons.append({"metric": metric, "period_label": current.period_label, "value": current.value, "unit": current.unit, "qoq_percent": qoq, "qoq_derived": qoq is not None, "yoy_percent": yoy, "yoy_derived": yoy is not None, "basis": current.basis, "source_url": current.source_url, "source_name": current.source_name})
    documents = db.scalars(select(ResearchDocument).where(ResearchDocument.company_id == company.id).order_by(ResearchDocument.published_at.desc())).all()
    guidance = db.scalars(select(ManagementGuidance).where(ManagementGuidance.company_id == company.id).order_by(ManagementGuidance.published_at.desc())).all()
    analytics = financial_analytics(db, company.id)
    analytics["ml_insights"].extend(market_analytics(db, company.id))
    return {
        "company": company,
        "provider_status": "unavailable" if provider_error else ("partial" if not results else "available"),
        "provider_error": provider_error,
        "is_demo": False,
        "comparisons": comparisons,
        "periods": periods,
        "documents": documents,
        "guidance": guidance,
        **analytics,
    }


def search_companies(db: Session, query: str) -> list[Company]:
    query = query.strip()
    if not query:
        return db.scalars(select(Company).order_by(Company.name).limit(50)).all()
    return db.scalars(select(Company).where(Company.ticker.ilike(f"%{query}%") | Company.name.ilike(f"%{query}%")).order_by(Company.name).limit(50)).all()
