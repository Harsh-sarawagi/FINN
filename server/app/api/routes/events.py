import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from app.config import get_settings
from app.database.connection import SessionLocal
from app.models import EventOutbox

router = APIRouter(prefix="/api/v1", tags=["events"])


def _event_frame(event: EventOutbox) -> str:
    payload = json.loads(event.payload)
    return f"id: {event.id}\nevent: {event.event_type}\ndata: {json.dumps(payload, separators=(',', ':'))}\n\n"


async def event_stream(request: Request, last_event_id: int) -> AsyncIterator[str]:
    settings = get_settings()
    heartbeat_seconds = max(5, settings.sse_heartbeat_seconds)
    yield "retry: 5000\n\n"
    yield "event: connected\ndata: {\"status\":\"connected\"}\n\n"
    cursor = last_event_id
    while True:
        if await request.is_disconnected():
            return
        db = SessionLocal()
        try:
            events = db.scalars(select(EventOutbox).where(EventOutbox.id > cursor).order_by(EventOutbox.id).limit(100)).all()
        finally:
            db.close()
        if events:
            for event in events:
                if await request.is_disconnected():
                    return
                cursor = event.id
                yield _event_frame(event)
        else:
            yield ": heartbeat\n\n"
        await asyncio.sleep(heartbeat_seconds)


@router.get("/events/stream")
async def stream_events(request: Request) -> StreamingResponse:
    raw_id = request.headers.get("last-event-id", "")
    try:
        last_event_id = int(raw_id) if raw_id else 0
    except ValueError:
        last_event_id = 0
    return StreamingResponse(
        event_stream(request, last_event_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )
