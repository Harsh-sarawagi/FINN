from pydantic import BaseModel


class AssistantQuestion(BaseModel):
    question: str
    exchange: str = "NSE"


class AssistantCitation(BaseModel):
    type: str
    label: str
    url: str
    source_name: str
    period: str | None = None
    reference: str | None = None
    basis: str | None = None


class AssistantCompany(BaseModel):
    ticker: str
    name: str
    exchange: str


class AssistantResponse(BaseModel):
    company: AssistantCompany
    question: str
    answer: str
    answer_type: str
    citations: list[AssistantCitation]
    evidence_count: int
