from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.schemas.research import CompanySearchResponse, ResearchResponse, SyncResearchRequest
from app.services.research import research_payload, resolve_company, search_companies, sync_research

router = APIRouter(prefix="/api/v1/research", tags=["pull research"])


@router.get("/compare")
def compare_research_companies(tickers: list[str] = Query(..., min_length=2, max_length=6), db: Session = Depends(get_db)):
    from sqlalchemy import select
    from app.models import Company
    companies = db.scalars(select(Company).where(Company.ticker.in_([ticker.upper() for ticker in tickers]))).all()
    return [
        {
            "company": {"ticker": company.ticker, "name": company.name, "exchange": company.exchange},
            "comparisons": research_payload(db, company)["comparisons"],
            "financial_health": research_payload(db, company)["financial_health"],
        }
        for company in companies
    ]


@router.get("/companies", response_model=list[CompanySearchResponse])
def research_companies(query: str = "", db: Session = Depends(get_db)):
    return [CompanySearchResponse.model_validate(company) for company in search_companies(db, query)]


@router.get("/companies/{ticker}", response_model=ResearchResponse)
def get_research(ticker: str, exchange: str = "NSE", db: Session = Depends(get_db)):
    from sqlalchemy import select
    from app.models import Company
    company = db.scalar(select(Company).where(Company.ticker == ticker.upper(), Company.exchange == exchange.upper()))
    if company is None:
        raise HTTPException(status_code=404, detail="Company is not in the catalog. Use POST /sync to resolve it through the provider.")
    return ResearchResponse.model_validate(research_payload(db, company))


@router.post("/sync", response_model=ResearchResponse)
def sync_company(payload: SyncResearchRequest, db: Session = Depends(get_db)):
    try:
        return ResearchResponse.model_validate(sync_research(db, payload.ticker, payload.exchange))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
