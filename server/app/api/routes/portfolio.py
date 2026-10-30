from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.schemas.portfolio import AddPortfolioMemberRequest, PortfolioMemberResponse
from app.services.portfolio import add_portfolio_member, list_portfolio, remove_portfolio_member

router = APIRouter(prefix="/api/v1", tags=["portfolio"])


@router.get("/portfolio", response_model=list[PortfolioMemberResponse])
def portfolio(db: Session = Depends(get_db)) -> list[PortfolioMemberResponse]:
    return [PortfolioMemberResponse.model_validate(member) for member in list_portfolio(db)]


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
