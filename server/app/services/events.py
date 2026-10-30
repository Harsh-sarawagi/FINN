import json

from sqlalchemy.orm import Session

from app.models import EventOutbox


def publish_event(db: Session, event_type: str, payload: dict | None = None) -> EventOutbox:
    event = EventOutbox(event_type=event_type, payload=json.dumps(payload or {}, separators=(",", ":")))
    db.add(event)
    db.commit()
    db.refresh(event)
    return event
