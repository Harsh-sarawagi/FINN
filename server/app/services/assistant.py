import io
import logging
import re
import json
import time
from datetime import UTC, datetime

import httpx
import fitz
import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Announcement, Company, FinancialResult, ManagementGuidance, ResearchDocument, ResearchDocumentChunk

logger = logging.getLogger(__name__)

METRIC_LABELS = {"revenue": "Revenue", "ebitda": "EBITDA", "pbt": "PBT", "pat": "PAT"}
RESEARCH_SYSTEM_PROMPT = """You are FINN's financial research analyst. Answer only from the structured evidence provided for the named company.

Rules:
- Separate REPORTED FACTS, DETERMINISTIC CALCULATIONS, MANAGEMENT GUIDANCE, DOCUMENT EXCERPTS, and AI INTERPRETATION.
- Do not calculate figures. Use only values and calculations supplied in evidence.
- Cite supporting evidence by its evidence_id when making a factual statement.
- Quote financial metrics exactly, including their unit, period, and consolidated/standalone basis.
- If evidence is missing or does not support the question, explicitly say so.
- Never invent figures, documents, page numbers, dates, citations, management statements, or company facts.
- Do not provide investment advice, price targets, or guarantees."""

_STOP_WORDS = {
    "about", "company", "give", "latest", "please", "what", "when", "where", "which", "who",
    "the", "this", "that", "have", "has", "was", "were", "are", "for", "and", "from", "with",
}


def _lexical_score(text: str, question_terms: set[str]) -> float:
    text_terms = _terms(text)
    meaningful_terms = question_terms - _STOP_WORDS
    if not meaningful_terms:
        return 0.0
    overlap = meaningful_terms & text_terms
    return (len(overlap) * 2.0 + sum(1.0 for term in overlap if len(term) >= 6)) / len(meaningful_terms)


def _ranked(items, text_getter, question_terms, limit: int):
    ranked = [
        (_lexical_score(text_getter(item), question_terms), item)
        for item in items
    ]
    ranked.sort(key=lambda pair: pair[0], reverse=True)
    return [item for score, item in ranked[:limit] if score > 0.0]


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


def _index_document(db: Session, document: ResearchDocument) -> None:
    if not document.extracted_text:
        return
    existing = db.scalar(select(ResearchDocumentChunk.id).where(ResearchDocumentChunk.document_id == document.id))
    if existing is not None:
        return
    settings = get_settings()
    chunks = []
    pages = re.split(r"\[Page (\d+)\]", document.extracted_text)
    for index in range(1, len(pages), 2):
        page_number = int(pages[index])
        page_text = pages[index + 1].strip() if index + 1 < len(pages) else ""
        words = page_text.split()
        for offset in range(0, max(1, len(words)), 220):
            content = " ".join(words[offset:offset + 260]).strip()
            if content:
                chunks.append((page_number, content))
    embeddings = []
    if settings.openai_api_key and chunks:
        try:
            response = httpx.post(
                "https://api.openai.com/v1/embeddings",
                headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                json={"model": settings.openai_embedding_model or "text-embedding-3-small", "input": [content for _, content in chunks]},
                timeout=30,
            )
            response.raise_for_status()
            embeddings = [item["embedding"] for item in response.json()["data"]]
        except Exception as exc:
            logger.warning("Document embedding unavailable: %s", exc)
    embedding_model = settings.openai_embedding_model or "text-embedding-3-small"
    for chunk_index, ((page_number, content), embedding) in enumerate(zip(chunks, embeddings + [None] * len(chunks))):
        db.add(ResearchDocumentChunk(
            document_id=document.id,
            chunk_index=chunk_index,
            page_number=page_number,
            content=content,
            embedding=json.dumps(embedding) if embedding else None,
            embedding_model=embedding_model if embedding else None,
        ))


def percentage_change(current: float, prior: float | None) -> float | None:
    if prior is None or prior == 0:
        return None
    return round(((current - prior) / abs(prior)) * 100, 2)


def _embed_query(question: str) -> list[float] | None:
    settings = get_settings()
    if settings.ai_api_key and not settings.openai_api_key:
        return None
    if not settings.openai_api_key:
        return None
    try:
        response = httpx.post(
            "https://api.openai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {settings.llm_api_key}"},
            json={"model": settings.openai_embedding_model or "text-embedding-3-small", "input": [question]},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["data"][0]["embedding"]
    except Exception as exc:
        logger.warning("Question embedding unavailable: %s", exc)
        return None


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
            "evidence_id": f"financial:{current.id}",
            "kind": "reported_financial", "metric": METRIC_LABELS[metric], "value": current.value,
            "unit": current.unit, "period": current.period_label, "basis": current.basis,
            "qoq_percent": percentage_change(current.value, prior_qoq), "yoy_percent": percentage_change(current.value, prior_yoy),
            "source_url": current.source_url, "source_name": current.source_name,
        })
        citations.append({"type": "reported_financial", "label": f"{METRIC_LABELS[metric]} {current.period_label}", "url": current.source_url, "source_name": current.source_name, "period": current.period_label, "reference": "Provider-reported financial metric", "basis": current.basis})

    announcements = db.scalars(select(Announcement).where(Announcement.company_id == company.id).order_by(Announcement.published_at.desc()).limit(40)).all()
    matched_announcements = _ranked(
        announcements,
        lambda announcement: f"{announcement.title} {announcement.content or ''}",
        terms,
        6,
    )
    if not matched_announcements and any(term in {"overview", "latest", "news", "update"} for term in terms):
        matched_announcements = announcements[:4]
    for announcement in matched_announcements:
        text = f"{announcement.title} {announcement.content or ''}"
        excerpt = _snippet(text, terms)
        evidence.append({"evidence_id": f"announcement:{announcement.id}", "kind": "announcement", "title": announcement.title, "excerpt": excerpt, "category": announcement.category, "published_at": announcement.published_at.isoformat(), "source_url": announcement.source_url})
        citations.append({"type": "announcement", "label": announcement.title, "url": announcement.source_url, "source_name": announcement.source_name, "period": announcement.published_at.isoformat(), "reference": "Announcement available in FINN"})
        if len(citations) >= 12:
            break

    documents = db.scalars(select(ResearchDocument).where(ResearchDocument.company_id == company.id).order_by(ResearchDocument.published_at.desc()).limit(15)).all()
    for document in documents:
        extract_document(document)
        _index_document(db, document)
        if document.extracted_text:
            excerpt = _snippet(document.extracted_text, terms)
            if terms and not (_terms(excerpt) & terms):
                continue
            evidence.append({"evidence_id": f"document:{document.id}", "kind": "document", "title": document.title, "excerpt": excerpt, "document_type": document.document_type, "source_url": document.source_url})
            citations.append({"type": "document", "label": document.title, "url": document.source_url, "source_name": document.source_name, "period": document.period_label, "reference": "Extracted document source; page reference may appear in excerpt"})

    document_ids = [document.id for document in documents if document.id]
    chunks = db.scalars(
        select(ResearchDocumentChunk).where(
            ResearchDocumentChunk.document_id.in_(document_ids) if document_ids else ResearchDocumentChunk.id == -1
        )
    ).all()
    lexical_ranked = _ranked(chunks, lambda chunk: chunk.content, terms, 6)
    retrieved_chunk_ids: set[int] = set()
    for chunk in lexical_ranked:
        document = db.get(ResearchDocument, chunk.document_id)
        evidence.append({
            "evidence_id": f"chunk:{chunk.id}",
            "kind": "keyword_document_chunk",
            "excerpt": chunk.content,
            "document_type": document.document_type if document else "document",
            "source_url": document.source_url if document else "",
            "page": chunk.page_number,
            "retrieval": "keyword_overlap",
        })
        retrieved_chunk_ids.add(chunk.id)
        if document:
            citations.append({"type": "document", "label": document.title, "url": document.source_url, "source_name": document.source_name, "period": document.period_label, "reference": f"Page {chunk.page_number}" if chunk.page_number else "Document section"})

    query_embedding = _embed_query(question)
    if query_embedding:
        chunks = db.scalars(
            select(ResearchDocumentChunk).where(
                ResearchDocumentChunk.document_id.in_(document_ids),
                ResearchDocumentChunk.embedding.is_not(None),
            ) if document_ids else ResearchDocumentChunk.id == -1
        ).all()
        ranked = []
        query_vector = np.asarray(query_embedding, dtype=float)
        for chunk in chunks:
            chunk_vector = np.asarray(json.loads(chunk.embedding), dtype=float)
            if chunk_vector.size and query_vector.size:
                similarity = float(np.dot(query_vector, chunk_vector) / (np.linalg.norm(query_vector) * np.linalg.norm(chunk_vector)))
                ranked.append((similarity, chunk))
        for similarity, chunk in sorted(ranked, reverse=True, key=lambda item: item[0])[:6]:
            if chunk.id in retrieved_chunk_ids:
                continue
            document = db.get(ResearchDocument, chunk.document_id)
            evidence.append({
                "evidence_id": f"chunk:{chunk.id}",
                "kind": "semantic_document_chunk",
                "excerpt": chunk.content,
                "document_type": document.document_type if document else "document",
                "source_url": document.source_url if document else "",
                "page": chunk.page_number,
                "similarity": round(similarity, 4),
                "retrieval": "semantic_embedding",
            })
            if document:
                citations.append({"type": "document", "label": document.title, "url": document.source_url, "source_name": document.source_name, "period": document.period_label, "reference": f"Page {chunk.page_number}" if chunk.page_number else "Semantic document excerpt"})

    guidance = db.scalars(select(ManagementGuidance).where(ManagementGuidance.company_id == company.id).order_by(ManagementGuidance.published_at.desc())).all()
    matched_guidance = _ranked(guidance, lambda item: item.statement, terms, 4) if guidance else []
    if not matched_guidance and any(term in {"guidance", "outlook", "forecast", "expects", "expectation"} for term in terms):
        matched_guidance = guidance[:4]
    for item in matched_guidance:
        evidence.append({"evidence_id": f"guidance:{item.id}", "kind": "management_guidance", "statement": item.statement, "source_url": item.source_url})
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
    if settings.llm_api_key and retrieved["evidence"]:
        context_payload = json.dumps(
            {
                "company": company.name,
                "ticker": company.ticker,
                "question": question,
                "evidence": retrieved["evidence"][:30],
            },
            ensure_ascii=False,
        )
        try:
            response = None
            for attempt in range(2):
                response = httpx.post(
                    settings.llm_api_url,
                    headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                    json={"model": settings.llm_model, "temperature": 0,
                          "messages": [{"role": "system", "content": RESEARCH_SYSTEM_PROMPT},
                                       {"role": "user", "content": context_payload}], "max_tokens": 700}, timeout=30)
                if response.status_code != 429:
                    break
                time.sleep(2 if attempt == 0 else 4)
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
