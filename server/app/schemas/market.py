from datetime import datetime
from pydantic import BaseModel, ConfigDict


class MarketPricePoint(BaseModel):
    price_date: str
    close: float


class MarketInstrument(BaseModel):
    ticker: str
    name: str
    exchange: str
    price: float | None
    change_percent: float | None
    volume: int | None
    price_date: str | None
    history: list[MarketPricePoint] = []


class DashboardMover(BaseModel):
    ticker: str
    name: str
    change_percent: float
    price: float


class MarketDashboard(BaseModel):
    live_data: bool
    is_demo_data: bool
    source: str
    last_updated: datetime | None
    portfolio_count: int
    portfolio_average_change: float | None
    advancing_count: int
    declining_count: int
    instruments: list[MarketInstrument]
    top_gainers: list[DashboardMover]
    top_losers: list[DashboardMover]


class MarketSyncResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status: str
    provider: str
    records_updated: int
    last_attempt_at: datetime | None
    last_success_at: datetime | None
    error_message: str | None = None
