from datetime import date, datetime
from pydantic import BaseModel, ConfigDict


class ResearchCompany(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    ticker: str
    name: str
    exchange: str


class FinancialComparison(BaseModel):
    metric: str
    period_label: str
    value: float | None
    unit: str
    qoq_percent: float | None
    qoq_derived: bool
    yoy_percent: float | None
    yoy_derived: bool
    basis: str
    source_url: str
    source_name: str


class FinancialPeriod(BaseModel):
    period_end: date
    period_label: str
    basis: str
    unit: str
    values: dict[str, float]


class ResearchDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    document_type: str
    source_url: str
    source_name: str
    published_at: datetime | None
    period_label: str | None


class GuidanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    statement: str
    period_label: str | None
    source_url: str
    source_name: str
    published_at: datetime | None
    extracted: bool


class ResearchResponse(BaseModel):
    company: ResearchCompany
    provider_status: str
    provider_error: str | None
    is_demo: bool
    comparisons: list[FinancialComparison]
    periods: list[FinancialPeriod]
    documents: list[ResearchDocumentResponse]
    guidance: list[GuidanceResponse]


class CompanySearchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    ticker: str
    name: str
    exchange: str


class SyncResearchRequest(BaseModel):
    ticker: str
    exchange: str = "NSE"
