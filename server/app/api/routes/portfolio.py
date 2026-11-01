from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.schemas.portfolio import AddPortfolioMemberRequest, CompanyResponse, DiscoverCompanyRequest, PortfolioHistoryResponse, PortfolioMemberResponse
from app.services.portfolio import add_portfolio_member, discover_company, list_companies, list_portfolio, list_portfolio_history, remove_portfolio_member

router = APIRouter(prefix="/api/v1", tags=["portfolio"])


@router.get("/portfolio", response_model=list[PortfolioMemberResponse])
def portfolio(db: Session = Depends(get_db)) -> list[PortfolioMemberResponse]:
    return [PortfolioMemberResponse.model_validate(member) for member in list_portfolio(db)]


@router.get("/companies", response_model=list[CompanyResponse])
def companies(q: str = Query(default="", max_length=100), db: Session = Depends(get_db)) -> list[CompanyResponse]:
    return [CompanyResponse.model_validate(company) for company in list_companies(db, q)]


@router.post("/companies/discover", response_model=CompanyResponse)
def discover(payload: DiscoverCompanyRequest, db: Session = Depends(get_db)) -> CompanyResponse:
    try:
        return CompanyResponse.model_validate(discover_company(db, payload.ticker, payload.exchange, payload.name))
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.get("/portfolio/history", response_model=list[PortfolioHistoryResponse])
def portfolio_history(db: Session = Depends(get_db)) -> list[PortfolioHistoryResponse]:
    return [PortfolioHistoryResponse.model_validate(item) for item in list_portfolio_history(db)]


@router.post("/portfolio", response_model=PortfolioMemberResponse, status_code=status.HTTP_201_CREATED)
def add_member(payload: AddPortfolioMemberRequest, db: Session = Depends(get_db)) -> PortfolioMemberResponse:
    try:
        member = add_portfolio_member(db, payload.ticker, payload.exchange)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    db.refresh(member, ["company"])
    return PortfolioMemberResponse.model_validate(member)


@router.delete("/portfolio/{ticker}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    ticker: str,
    exchange: str = Query(default="NSE"),
    db: Session = Depends(get_db),
) -> None:
    try:
        remove_portfolio_member(db, ticker, exchange)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
