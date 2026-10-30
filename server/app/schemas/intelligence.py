from datetime import datetime
from pydantic import BaseModel, ConfigDict


class AnnouncementCompany(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    ticker: str
    name: str
    exchange: str


class AnnouncementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    company: AnnouncementCompany
    title: str
    content: str | None
    category: str
    source_url: str
    source_name: str
    published_at: datetime
    ingested_at: datetime
    ingestion_status: str
    summary: str | None
    ai_generated: bool
    is_demo: bool


class IngestionStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    status: str
    source: str
    last_attempt_at: datetime | None
    last_success_at: datetime | None
    records_added: int
    error_message: str | None


class AlertRuleRequest(BaseModel):
    name: str
    category: str | None = None
    company_id: int | None = None
    enabled: bool = True


class AlertRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    category: str | None
    company_id: int | None
    enabled: bool
    created_at: datetime


class AlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    message: str | None
    is_read: bool
    created_at: datetime
    announcement: AnnouncementResponse


class DailyDigestResponse(BaseModel):
    generated_at: datetime
    period_hours: int
    announcement_count: int
    by_category: dict[str, int]
    announcements: list[AnnouncementResponse]
