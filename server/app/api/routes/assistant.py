from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models import Company
from app.schemas.assistant import AssistantQuestion, AssistantResponse
from app.services.assistant import answer_research_question

router = APIRouter(prefix="/api/v1/research", tags=["AI research assistant"])


@router.post("/assistant/{ticker}", response_model=AssistantResponse)
def ask_research_assistant(ticker: str, payload: AssistantQuestion, db: Session = Depends(get_db)):
    if not payload.question.strip():
        raise HTTPException(status_code=422, detail="Question cannot be empty")
    company = db.scalar(select(Company).where(Company.ticker == ticker.upper(), Company.exchange == payload.exchange.upper()))
    if company is None:
        raise HTTPException(status_code=404, detail="Company is not in the catalog. Sync the company research data first.")
    result = answer_research_question(db, company, payload.question.strip())
    result["company"] = {"ticker": company.ticker, "name": company.name, "exchange": company.exchange}
    return AssistantResponse.model_validate(result)
