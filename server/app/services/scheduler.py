import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import text

from app.config import get_settings
from app.database.connection import SessionLocal, engine
from app.services.announcements import sync_announcements
from app.services.market_data import sync_portfolio_market_data

logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler(timezone="UTC")
MARKET_JOB_LOCK = 4101
ANNOUNCEMENT_JOB_LOCK = 4102


def _run_with_lock(lock_id: int, job_name: str, callback) -> None:
    connection = engine.connect()
    acquired = False
    try:
        acquired = bool(connection.execute(text("SELECT pg_try_advisory_lock(:lock_id)"), {"lock_id": lock_id}).scalar())
        if not acquired:
            logger.info("Skipping overlapping %s job", job_name)
            return
        db = SessionLocal()
        try:
            callback(db)
            logger.info("Completed scheduled %s job", job_name)
        finally:
            db.close()
    except Exception:
        logger.exception("Scheduled %s job failed", job_name)
    finally:
        if acquired:
            connection.execute(text("SELECT pg_advisory_unlock(:lock_id)"), {"lock_id": lock_id})
        connection.close()


def run_market_ingestion() -> None:
    _run_with_lock(MARKET_JOB_LOCK, "market ingestion", sync_portfolio_market_data)


def run_announcement_ingestion() -> None:
    _run_with_lock(ANNOUNCEMENT_JOB_LOCK, "announcement ingestion", sync_announcements)


def start_scheduler() -> None:
    settings = get_settings()
    if not settings.scheduler_enabled or scheduler.running:
        return
    scheduler.add_job(run_market_ingestion, IntervalTrigger(minutes=max(5, settings.market_ingestion_interval_minutes), timezone="UTC"), id="market-ingestion", replace_existing=True, max_instances=1, coalesce=True)
    scheduler.add_job(run_announcement_ingestion, IntervalTrigger(minutes=max(5, settings.announcement_ingestion_interval_minutes), timezone="UTC"), id="announcement-ingestion", replace_existing=True, max_instances=1, coalesce=True)
    scheduler.start()
    if settings.scheduler_run_on_startup:
        run_market_ingestion()
        run_announcement_ingestion()
