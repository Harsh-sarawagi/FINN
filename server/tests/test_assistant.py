from app.services.assistant import _financial_question_matches, percentage_change


def test_assistant_uses_deterministic_percentage_calculation():
    assert percentage_change(125, 100) == 25.0


def test_assistant_handles_missing_or_zero_prior():
    assert percentage_change(125, None) is None
    assert percentage_change(125, 0) is None


def test_financial_question_matching_is_restricted():
    assert _financial_question_matches("What is the latest revenue?", "revenue")
    assert _financial_question_matches("Give a financial overview", "pat")
    assert not _financial_question_matches("Did a cricket stadium announcement occur?", "revenue")
