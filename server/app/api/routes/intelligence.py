from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models import Alert, AlertRule, Announcement, AnnouncementIngestionStatus
from app.schemas.intelligence import (
    AlertResponse, AlertRuleRequest, AlertRuleResponse, AnnouncementResponse,
    DailyDigestResponse, IngestionStatusResponse,
)
from app.services.announcements import create_alerts, get_daily_digest, list_announcements, sync_announcements
from app.services.events import publish_event

router = APIRouter(prefix="/api/v1", tags=["push intelligence"])


@router.post("/announcements/ingest", response_model=IngestionStatusResponse)
def ingest_announcements(db: Session = Depends(get_db)) -> IngestionStatusResponse:
    return IngestionStatusResponse.model_validate(sync_announcements(db))


@router.get("/announcements/status", response_model=IngestionStatusResponse)
def announcement_status(db: Session = Depends(get_db)) -> IngestionStatusResponse:
    status = db.scalar(select(AnnouncementIngestionStatus).order_by(AnnouncementIngestionStatus.id.desc()))
    if status is None:
        return IngestionStatusResponse(status="never_run", source="NSE/BSE", last_attempt_at=None, last_success_at=None, records_added=0, error_message=None)
    return IngestionStatusResponse.model_validate(status)


@router.get("/announcements", response_model=list[AnnouncementResponse])
def announcements(category: str | None = None, company_id: int | None = None, limit: int = Query(default=50, ge=1, le=200), db: Session = Depends(get_db)):
    return [AnnouncementResponse.model_validate(item) for item in list_announcements(db, category, company_id, limit)]


@router.get("/digest/daily", response_model=DailyDigestResponse)
def daily_digest(db: Session = Depends(get_db)) -> DailyDigestResponse:
    return DailyDigestResponse.model_validate(get_daily_digest(db))


@router.get("/alert-rules", response_model=list[AlertRuleResponse])
def alert_rules(db: Session = Depends(get_db)):
    return db.scalars(select(AlertRule).order_by(AlertRule.id)).all()


@router.post("/alert-rules", response_model=AlertRuleResponse, status_code=201)
def create_alert_rule(payload: AlertRuleRequest, db: Session = Depends(get_db)):
    rule = AlertRule(**payload.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    for announcement in db.scalars(select(Announcement).order_by(Announcement.id)).all():
        create_alerts(db, announcement)
    db.commit()
    publish_event(db, "notifications.updated", {"reason": "alert-rule-created"})
    return rule


@router.get("/alerts", response_model=list[AlertResponse])
def alerts(unread_only: bool = False, db: Session = Depends(get_db)):
    statement = select(Alert).order_by(Alert.created_at.desc())
    if unread_only:
        statement = statement.where(Alert.is_read.is_(False))
    return db.scalars(statement).all()


@router.patch("/alerts/{alert_id}/read", response_model=AlertResponse)
def mark_alert_read(alert_id: int, db: Session = Depends(get_db)):
    alert = db.get(Alert, alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.is_read = True
    db.commit()
    db.refresh(alert)
    publish_event(db, "notifications.updated", {"alert_id": alert.id, "read": True})
    return alert
