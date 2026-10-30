import io
import logging
import re
from datetime import UTC, datetime

import httpx
import fitz
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Announcement, Company, FinancialResult, ManagementGuidance, ResearchDocument

logger = logging.getLogger(__name__)

METRIC_LABELS = {"revenue": "Revenue", "ebitda": "EBITDA", "pbt": "PBT", "pat": "PAT"}


def _financial_question_matches(question: str, metric: str) -> bool:
    terms = _terms(question)
    return bool(terms & {metric, METRIC_LABELS[metric].lower(), "financial", "financials", "result", "results", "quarter", "quarterly", "earnings", "performance", "overview", "company"})


def _terms(text: str) -> set[str]:
    return {value for value in re.findall(r"[a-z0-9]+", text.lower()) if len(value) > 2}


def _snippet(text: str, question_terms: set[str], limit: int = 700) -> str:
    clean = re.sub(r"\s+", " ", text).strip()
    if len(clean) <= limit:
        return clean
    sentences = re.split(r"(?<=[.!?])\s+", clean)
    ranked = sorted(sentences, key=lambda sentence: len(_terms(sentence) & question_terms), reverse=True)
    selected = [sentence for sentence in ranked if _terms(sentence) & question_terms][:3]
    return re.sub(r"\s+", " ", " ".join(selected or sentences[:2]))[:limit]


def extract_document(document: ResearchDocument) -> None:
    if document.extracted_text:
        return
    if document.content_status == "unavailable":
        return
    try:
        with httpx.Client(follow_redirects=True, timeout=30, headers={"User-Agent": "FINN research assistant"}) as client:
            response = client.get(document.source_url)
            response.raise_for_status()
            pdf = fitz.open(stream=io.BytesIO(response.content), filetype="pdf")
            pages = [page.get_text("text") for page in pdf if page.get_text("text")]
            text = "\n".join(f"[Page {index + 1}] {page}" for index, page in enumerate(pages))
            if not text.strip():
                document.content_status = "no_extractable_text"
            else:
                document.extracted_text = text[:150000]
                document.content_status = "extracted"
                document.extracted_at = datetime.now(UTC)
    except Exception as exc:
        logger.warning("Document extraction failed for %s: %s", document.source_url, exc)
        document.content_status = "unavailable"


def percentage_change(current: float, prior: float | None) -> float | None:
    if prior is None or prior == 0:
        return None
    return round(((current - prior) / abs(prior)) * 100, 2)


def retrieve_context(db: Session, company: Company, question: str) -> dict:
    terms = _terms(question)
    citations = []
    evidence = []

    results = db.scalars(select(FinancialResult).where(FinancialResult.company_id == company.id).order_by(FinancialResult.period_end.desc())).all()
    grouped: dict[str, list[FinancialResult]] = {metric: [] for metric in METRIC_LABELS}
    for result in results:
        if result.metric in grouped:
            grouped[result.metric].append(result)
    for metric, rows in grouped.items():
        if not rows or not _financial_question_matches(question, metric):
            continue
        rows.sort(key=lambda row: row.period_end, reverse=True)
        current = rows[0]
        prior_qoq = rows[1].value if len(rows) > 1 else None
        prior_yoy = rows[4].value if len(rows) > 4 else None
        evidence.append({
            "kind": "reported_financial", "metric": METRIC_LABELS[metric], "value": current.value,
            "unit": current.unit, "period": current.period_label, "basis": current.basis,
            "qoq_percent": percentage_change(current.value, prior_qoq), "yoy_percent": percentage_change(current.value, prior_yoy),
            "source_url": current.source_url, "source_name": current.source_name,
        })
        citations.append({"type": "reported_financial", "label": f"{METRIC_LABELS[metric]} {current.period_label}", "url": current.source_url, "source_name": current.source_name, "period": current.period_label, "reference": "Provider-reported financial metric", "basis": current.basis})

    announcements = db.scalars(select(Announcement).where(Announcement.company_id == company.id).order_by(Announcement.published_at.desc()).limit(40)).all()
    for announcement in announcements:
        text = f"{announcement.title} {announcement.content or ''}"
        if terms and not (_terms(text) & terms):
            continue
        excerpt = _snippet(text, terms)
        evidence.append({"kind": "announcement", "title": announcement.title, "excerpt": excerpt, "category": announcement.category, "published_at": announcement.published_at.isoformat(), "source_url": announcement.source_url})
        citations.append({"type": "announcement", "label": announcement.title, "url": announcement.source_url, "source_name": announcement.source_name, "period": announcement.published_at.isoformat(), "reference": "Announcement available in FINN"})
        if len(citations) >= 12:
            break

    documents = db.scalars(select(ResearchDocument).where(ResearchDocument.company_id == company.id).order_by(ResearchDocument.published_at.desc()).limit(15)).all()
    for document in documents:
        extract_document(document)
        if document.extracted_text:
            excerpt = _snippet(document.extracted_text, terms)
            if terms and not (_terms(excerpt) & terms):
                continue
            evidence.append({"kind": "document", "title": document.title, "excerpt": excerpt, "document_type": document.document_type, "source_url": document.source_url})
            citations.append({"type": "document", "label": document.title, "url": document.source_url, "source_name": document.source_name, "period": document.period_label, "reference": "Extracted document source; page reference may appear in excerpt"})

    guidance = db.scalars(select(ManagementGuidance).where(ManagementGuidance.company_id == company.id).order_by(ManagementGuidance.published_at.desc())).all()
    for item in guidance:
        if terms and not (_terms(item.statement) & terms):
            continue
        evidence.append({"kind": "management_guidance", "statement": item.statement, "source_url": item.source_url})
        citations.append({"type": "management_guidance", "label": "Management guidance", "url": item.source_url, "source_name": item.source_name, "period": item.period_label, "reference": "Management guidance source"})

    db.commit()
    return {"evidence": evidence, "citations": citations[:12], "company": company}


def answer_research_question(db: Session, company: Company, question: str) -> dict:
    retrieved = retrieve_context(db, company, question)
    settings = get_settings()
    fallback = (
        "FINN has source-backed evidence, but no AI provider key is configured. "
        "Review the cited reported facts and available excerpts below rather than inferring unsupported conclusions."
    )
    if not retrieved["evidence"]:
        fallback = "No stored financial metrics, announcements, guidance, or extractable document content supports an answer to this question."
    answer = fallback
    ai_generated = False
    if settings.openai_api_key and retrieved["evidence"]:
        context = "\n".join(str(item) for item in retrieved["evidence"][:30])
        try:
            response = httpx.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                json={"model": settings.openai_model or "gpt-4o-mini", "temperature": 0,
                      "messages": [{"role": "system", "content": "Answer only using the provided FINN evidence. Keep reported facts, management guidance, deterministic calculations, and AI interpretation clearly separated. Do not calculate figures, invent citations, or infer missing data. If unsupported, say the evidence is insufficient."},
                                   {"role": "user", "content": f"Company: {company.name}\nQuestion: {question}\nEvidence: {context}"}], "max_tokens": 500}, timeout=30)
            response.raise_for_status()
            answer = response.json()["choices"][0]["message"]["content"].strip()
            ai_generated = True
        except Exception as exc:
            logger.warning("AI research answer unavailable: %s", exc)
            answer = fallback + " The AI provider request also failed; this response contains no provider-generated interpretation."
    return {
        "company": company,
        "question": question,
        "answer": answer,
        "answer_type": "ai_generated" if ai_generated else "source_grounded_fallback",
        "citations": retrieved["citations"],
        "evidence_count": len(retrieved["evidence"]),
    }
