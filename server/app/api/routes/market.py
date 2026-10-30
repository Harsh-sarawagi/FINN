from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.schemas.market import MarketDashboard, MarketSyncResponse
from app.services.market_data import get_dashboard, sync_portfolio_market_data

router = APIRouter(prefix="/api/v1", tags=["market"])


@router.get("/dashboard", response_model=MarketDashboard)
def dashboard(db: Session = Depends(get_db)) -> MarketDashboard:
    return MarketDashboard.model_validate(get_dashboard(db))


@router.post("/market/sync", response_model=MarketSyncResponse)
def sync_market(db: Session = Depends(get_db)) -> MarketSyncResponse:
    return MarketSyncResponse.model_validate(sync_portfolio_market_data(db))


@router.get("/market/status", response_model=MarketSyncResponse)
def market_status(db: Session = Depends(get_db)) -> MarketSyncResponse:
    from sqlalchemy import select
    from app.models import MarketSyncStatus

    status = db.scalar(select(MarketSyncStatus).order_by(MarketSyncStatus.id.desc()))
    if status is None:
        return MarketSyncResponse(status="never_run", provider="yfinance", records_updated=0, last_attempt_at=None, last_success_at=None)
    return MarketSyncResponse.model_validate(status)
