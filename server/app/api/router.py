from fastapi import APIRouter

from app.api.routes.health import router as health_router
from app.api.routes.market import router as market_router
from app.api.routes.portfolio import router as portfolio_router
from app.api.routes.intelligence import router as intelligence_router
from app.api.routes.research import router as research_router
from app.api.routes.assistant import router as assistant_router
from app.api.routes.events import router as events_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(portfolio_router)
api_router.include_router(market_router)
api_router.include_router(intelligence_router)
api_router.include_router(research_router)
api_router.include_router(assistant_router)
api_router.include_router(events_router)
