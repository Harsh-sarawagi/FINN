from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CompanyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticker: str
    name: str
    exchange: str


class PortfolioMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    added_at: datetime
    company: CompanyResponse
    is_active: bool = True
    removed_at: datetime | None = None
    previous_status: str = "active"


class AddPortfolioMemberRequest(BaseModel):
    ticker: str = Field(min_length=1, max_length=20)
    exchange: str = Field(default="NSE", min_length=2, max_length=10)


class DiscoverCompanyRequest(BaseModel):
    ticker: str = Field(min_length=1, max_length=20)
    exchange: str = Field(default="NSE")
    name: str | None = Field(default=None, max_length=200)


class PortfolioHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    company_id: int
    action: str
    previous_status: str
    occurred_at: datetime
    company: CompanyResponse
