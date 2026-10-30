import hashlib
import logging
from datetime import UTC, datetime, timedelta
from html import unescape
from re import sub

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Announcement, AnnouncementIngestionStatus, Alert, AlertRule, Company, PortfolioMember
from app.services.events import publish_event

logger = logging.getLogger(__name__)

CATEGORY_KEYWORDS = {
    "financial_results": ("financial results", "quarterly results", "unaudited", "standalone", "consolidated", "revenue", "profit"),
    "corporate_actions": ("dividend", "bonus", "split", "buyback", "rights issue", "record date"),
    "major_orders": ("order", "contract", "work order", "tender", "award"),
    "management_updates": ("management", "director", "resignation", "appointment", "chief executive", "ceo", "cfo"),
}


def classify_announcement(text: str) -> str:
    normalized = text.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in normalized for keyword in keywords):
            return category
    return "other_material"


def extractive_summary(title: str, content: str | None) -> str:
    source_text = (content or title).strip()
    plain = unescape(sub(r"<[^>]+>", " ", source_text))
    plain = " ".join(plain.split())
    return plain[:300] + ("…" if len(plain) > 300 else "")


def ai_summary(title: str, content: str | None) -> tuple[str, bool]:
    settings = get_settings()
    source = (content or title).strip()
    if not settings.openai_api_key or not source:
        return extractive_summary(title, content), False
    try:
        response = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            json={
                "model": settings.openai_model or "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "Summarize only the supplied announcement. Do not add facts or speculate. Return two concise sentences maximum."},
                    {"role": "user", "content": f"Title: {title}\nAvailable content: {source[:5000]}"},
                ],
                "temperature": 0,
                "max_tokens": 160,
            },
            timeout=20,
        )
        response.raise_for_status()
        summary = response.json()["choices"][0]["message"]["content"].strip()
        return summary, bool(summary)
    except Exception as exc:
        logger.warning("AI summary unavailable: %s", exc)
        return extractive_summary(title, content), False


def parse_published(value: object) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    for fmt in ("%d-%b-%Y %H:%M:%S", "%d-%b-%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(text, fmt)
            return parsed.replace(tzinfo=UTC)
        except ValueError:
            continue
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    except ValueError:
        return None


def fetch_nse_announcements(company: Company, session: httpx.Client) -> list[dict]:
    to_date = datetime.now(UTC).strftime("%d-%m-%Y")
    from_date = (datetime.now(UTC) - timedelta(days=30)).strftime("%d-%m-%Y")
    session.get("https://www.nseindia.com", timeout=20).raise_for_status()
    response = session.get(
        "https://www.nseindia.com/api/corporate-announcements",
        params={"index": "equities", "symbol": company.ticker, "from_date": from_date, "to_date": to_date},
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list):
        return []
    records = []
    for item in payload:
        if str(item.get("symbol", "")).upper() != company.ticker.upper():
            continue
        title = str(item.get("subject") or item.get("desc") or "Corporate announcement")
        file_url = item.get("attchmntFile") or item.get("attchmntText")
        source_url = str(file_url).strip() if file_url else "https://www.nseindia.com/companies-listing/corporate-filings-announcements"
        if source_url.startswith("/"):
            source_url = "https://www.nseindia.com" + source_url
        published = parse_published(item.get("an_dt") or item.get("attchmntDate") or item.get("dt"))
        if not published:
            continue
        records.append({"title": title, "content": str(item.get("attchmntText") or item.get("desc") or title), "source_url": source_url, "source_name": "NSE", "published_at": published, "external_id": item.get("bm_eq_sr_no") or item.get("an_dt")})
    return records


def fetch_bse_announcements(company: Company, session: httpx.Client) -> list[dict]:
    response = session.get(
        "https://api.bseindia.com/BseIndiaAPI/api/AnnGetData/w",
        params={"strCat": "-1", "strPrevDate": "", "strScrip": "", "strSearch": "P", "strToDate": "", "strType": "C"},
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    records = []
    for item in payload.get("Table", []) if isinstance(payload, dict) else []:
        if str(item.get("SCRIP_CD") or "").upper() != company.ticker.upper():
            continue
        title = str(item.get("HEADLINE") or item.get("NEWSSUB") or "Corporate announcement")
        path = item.get("ATTACHMENTNAME") or item.get("PDF_NAME")
        source_url = str(path) if str(path).startswith("http") else "https://www.bseindia.com/corporates/ann.html"
        published = parse_published(item.get("NEWS_DT") or item.get("DT_TM") or item.get("DissemDT"))
        if published:
            records.append({"title": title, "content": str(item.get("MORE") or item.get("NEWS_SUB") or title), "source_url": source_url, "source_name": "BSE", "published_at": published, "external_id": item.get("NEWSID")})
    return records


def create_alerts(db: Session, announcement: Announcement) -> None:
    rules = db.scalars(select(AlertRule).where(AlertRule.enabled.is_(True))).all()
    for rule in rules:
        if rule.company_id not in (None, announcement.company_id):
            continue
        if rule.category and rule.category != announcement.category:
            continue
        existing = db.scalar(select(Alert.id).where(Alert.rule_id == rule.id, Alert.announcement_id == announcement.id))
        if existing:
            continue
        db.add(Alert(rule_id=rule.id, announcement_id=announcement.id, title=announcement.title, message=announcement.summary))


def sync_announcements(db: Session) -> AnnouncementIngestionStatus:
    status = AnnouncementIngestionStatus(source="NSE/BSE", status="running", last_attempt_at=datetime.now(UTC), records_added=0)
    db.add(status)
    db.commit()
    added = 0
    errors = []
    companies = db.scalars(select(Company).join(PortfolioMember, PortfolioMember.company_id == Company.id)).unique().all()
    headers = {"User-Agent": "Mozilla/5.0 FINN Market Intelligence", "Accept-Language": "en-US,en;q=0.9"}
    try:
        with httpx.Client(headers=headers, follow_redirects=True) as session:
            for company in companies:
                try:
                    records = fetch_bse_announcements(company, session) if company.exchange.upper() == "BSE" else fetch_nse_announcements(company, session)
                    for record in records:
                        fingerprint_source = f"{company.id}|{record['source_url']}|{record['published_at'].isoformat()}"
                        fingerprint = hashlib.sha256(fingerprint_source.encode()).hexdigest()
                        existing = db.scalar(select(Announcement).where(Announcement.fingerprint == fingerprint))
                        if existing:
                            continue
                        summary, ai_generated = ai_summary(record["title"], record["content"])
                        announcement = Announcement(
                            company_id=company.id, title=record["title"], content=record["content"],
                            category=classify_announcement(f"{record['title']} {record['content']}"),
                            source_url=record["source_url"], source_name=record["source_name"], published_at=record["published_at"],
                            external_id=str(record["external_id"]) if record["external_id"] else None, fingerprint=fingerprint,
                            summary=summary, ai_generated=ai_generated, ingestion_status="received",
                        )
                        db.add(announcement)
                        db.flush()
                        create_alerts(db, announcement)
                        added += 1
                except Exception as exc:
                    errors.append(f"{company.ticker}: {str(exc)[:200]}")
                    logger.warning("Announcement ingestion failed for %s: %s", company.ticker, exc)
        db.commit()
        status.status = "ok" if added else ("partial" if errors else "no_new_records")
        status.last_success_at = datetime.now(UTC) if not errors else status.last_success_at
        status.records_added = added
        status.error_message = "; ".join(errors[:5]) if errors else None
        db.commit()
        if added:
            publish_event(db, "announcements.updated", {"records_added": added})
            publish_event(db, "intelligence.updated", {"records_added": added})
            publish_event(db, "notifications.updated", {"records_added": added})
    except Exception as exc:
        db.rollback()
        status.status = "failed"
        status.records_added = 0
        status.error_message = str(exc)[:1000]
        db.commit()
    return status


def list_announcements(db: Session, category: str | None = None, company_id: int | None = None, limit: int = 50):
    statement = select(Announcement).order_by(Announcement.published_at.desc()).limit(limit)
    if category:
        statement = statement.where(Announcement.category == category)
    if company_id:
        statement = statement.where(Announcement.company_id == company_id)
    return db.scalars(statement).unique().all()


def get_daily_digest(db: Session):
    since = datetime.now(UTC) - timedelta(hours=24)
    announcements = db.scalars(select(Announcement).where(Announcement.published_at >= since).order_by(Announcement.published_at.desc())).all()
    by_category: dict[str, int] = {}
    for announcement in announcements:
        by_category[announcement.category] = by_category.get(announcement.category, 0) + 1
    return {"generated_at": datetime.now(UTC), "period_hours": 24, "announcement_count": len(announcements), "by_category": by_category, "announcements": announcements[:10]}
