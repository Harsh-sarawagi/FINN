from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError

from app.database.connection import check_database_connection
from app.schemas.health import DatabaseHealthResponse, HealthResponse, RootResponse

router = APIRouter(tags=["health"])


@router.get("/", response_model=RootResponse)
def root() -> RootResponse:
    return RootResponse(name="FINN API", status="running", docs="/docs")


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/health/db", response_model=DatabaseHealthResponse)
def database_health() -> DatabaseHealthResponse:
    try:
        check_database_connection()
    except (SQLAlchemyError, OSError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection unavailable",
        ) from exc
    return DatabaseHealthResponse(status="ok", database="connected")
