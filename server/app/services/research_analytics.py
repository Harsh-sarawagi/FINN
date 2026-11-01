from statistics import median

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import FinancialResult, MarketPrice


def _latest(rows: list[FinancialResult], metric: str) -> FinancialResult | None:
    matches = [row for row in rows if row.metric == metric]
    return sorted(matches, key=lambda row: row.period_end, reverse=True)[0] if matches else None


def _prior(rows: list[FinancialResult], metric: str, offset: int) -> FinancialResult | None:
    matches = sorted((row for row in rows if row.metric == metric), key=lambda row: row.period_end, reverse=True)
    return matches[offset] if len(matches) > offset else None


def robust_z(values: list[float]) -> float | None:
    if len(values) < 3:
        return None
    center = float(median(values[:-1]))
    deviations = [abs(value - center) for value in values[:-1]]
    mad = float(median(deviations)) if deviations else 0
    scale = 1.4826 * mad
    if scale <= 1e-9:
        return 0.0 if abs(values[-1] - center) <= 1e-9 else float("inf")
    return (values[-1] - center) / scale


def financial_analytics(db: Session, company_id: int) -> dict:
    rows = db.scalars(select(FinancialResult).where(FinancialResult.company_id == company_id).order_by(FinancialResult.period_end.desc())).all()
    revenue = _latest(rows, "revenue")
    ebitda = _latest(rows, "ebitda")
    pat = _latest(rows, "pat")
    debt = _latest(rows, "total_debt")
    equity = _latest(rows, "total_equity")
    cash_flow = _latest(rows, "operating_cash_flow")
    current_assets = _latest(rows, "current_assets")
    current_liabilities = _latest(rows, "current_liabilities")

    def ratio(numerator: FinancialResult | None, denominator: FinancialResult | None) -> float | None:
        if not numerator or not denominator or denominator.value == 0:
            return None
        return round(numerator.value / denominator.value * 100, 2)

    debt_equity = None
    if debt and equity and equity.value != 0:
        debt_equity = round(debt.value / equity.value, 2)
    current_ratio = None
    if current_assets and current_liabilities and current_liabilities.value != 0:
        current_ratio = round(current_assets.value / current_liabilities.value, 2)

    findings = []
    for metric in ("revenue", "ebitda", "pat"):
        values = [row.value for row in sorted((row for row in rows if row.metric == metric), key=lambda row: row.period_end)]
        if len(values) >= 3:
            score = robust_z(values)
            if score is not None and np.isfinite(score) and abs(score) >= 3.5:
                direction = "increase" if score > 0 else "decline"
                findings.append({
                    "category": "financial_change",
                    "metric": metric,
                    "severity": "notable",
                    "title": f"Unusual {metric.upper()} {direction}",
                    "explanation": f"The latest value is unusual relative to the prior pattern (robust z-score {round(score, 2)}).",
                    "source_type": "reported_financial",
                    "is_prediction": False,
                })

    periods = []
    for period in sorted({row.period_end for row in rows}, reverse=True):
        period_rows = {row.metric: row.value for row in rows if row.period_end == period}
        if not any(metric in period_rows for metric in ("revenue", "ebitda", "pat")):
            continue
        periods.append({
            "period_end": period,
            "revenue": period_rows.get("revenue"),
            "ebitda": period_rows.get("ebitda"),
            "pat": period_rows.get("pat"),
            "ebitda_margin": round(period_rows["ebitda"] / period_rows["revenue"] * 100, 2) if period_rows.get("revenue") and period_rows.get("ebitda") is not None else None,
            "pat_margin": round(period_rows["pat"] / period_rows["revenue"] * 100, 2) if period_rows.get("revenue") and period_rows.get("pat") is not None else None,
        })

    return {
        "financial_health": {
            "ebitda_margin_percent": ratio(ebitda, revenue),
            "pat_margin_percent": ratio(pat, revenue),
            "debt_to_equity": debt_equity,
            "current_ratio": current_ratio,
            "operating_cash_flow": cash_flow.value if cash_flow else None,
        },
        "trend": sorted(periods, key=lambda item: item["period_end"]),
        "ml_insights": findings,
        "model_scope": "Explanatory robust z-score screening on stored financial and market history; not a prediction or recommendation.",
    }


def market_analytics(db: Session, company_id: int) -> list[dict]:
    prices = db.scalars(select(MarketPrice).where(MarketPrice.company_id == company_id).order_by(MarketPrice.price_date)).all()
    if len(prices) < 6:
        return []
    returns = [
        ((current.close / previous.close) - 1) * 100
        for previous, current in zip(prices, prices[1:])
        if previous.close
    ]
    volumes = [float(row.volume) for row in prices if row.volume is not None]
    findings = []
    price_score = robust_z(returns) if returns else None
    volume_score = robust_z(volumes) if volumes else None
    if price_score is not None and np.isfinite(price_score) and abs(price_score) >= 3.5:
        findings.append({
            "category": "trading_activity",
            "metric": "daily_return",
            "severity": "notable",
            "title": "Abnormal daily price movement",
            "explanation": f"The latest return is unusual relative to prior returns (robust z-score {round(price_score, 2)}).",
            "is_prediction": False,
        })
    if volume_score is not None and np.isfinite(volume_score) and abs(volume_score) >= 3.5:
        findings.append({
            "category": "trading_activity",
            "metric": "volume",
            "severity": "notable",
            "title": "Abnormal trading volume",
            "explanation": f"The latest volume is unusual relative to prior observations (robust z-score {round(volume_score, 2)}).",
            "is_prediction": False,
        })
    return findings
