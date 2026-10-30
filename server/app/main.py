from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.api.router import api_router
from app.config import get_settings
from app.services.scheduler import start_scheduler

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    start_scheduler()
    yield
    from app.services.scheduler import scheduler
    if scheduler.running:
        scheduler.shutdown(wait=False)

app = FastAPI(
    title=settings.app_name,
    description="Backend foundation for the FINN investment intelligence prototype",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(api_router)
