from app.services.assistant import (
    RESEARCH_SYSTEM_PROMPT,
    _financial_question_matches,
    _ranked,
    percentage_change,
)


def test_assistant_uses_deterministic_percentage_calculation():
    assert percentage_change(125, 100) == 25.0


def test_assistant_handles_missing_or_zero_prior():
    assert percentage_change(125, None) is None
    assert percentage_change(125, 0) is None


def test_financial_question_matching_is_restricted():
    assert _financial_question_matches("What is the latest revenue?", "revenue")
    assert _financial_question_matches("Give a financial overview", "pat")
    assert not _financial_question_matches("Did a cricket stadium announcement occur?", "revenue")


def test_lexical_ranking_prefers_question_relevant_chunks():
    chunks = [
        {"content": "The company appointed a cricket stadium sponsor"},
        {"content": "Revenue increased and management discussed operating margins"},
    ]
    ranked = _ranked(chunks, lambda chunk: chunk["content"], {"revenue", "margin"}, 1)
    assert ranked == [chunks[1]]


def test_research_prompt_requires_supported_company_evidence():
    assert "evidence_id" in RESEARCH_SYSTEM_PROMPT
    assert "Never invent" in RESEARCH_SYSTEM_PROMPT
