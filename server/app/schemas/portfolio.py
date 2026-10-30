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


class AddPortfolioMemberRequest(BaseModel):
    ticker: str = Field(min_length=1, max_length=20)
    exchange: str = Field(default="NSE", min_length=2, max_length=10)
