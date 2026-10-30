from app.services.announcements import classify_announcement, extractive_summary


def test_classifies_financial_results():
    assert classify_announcement("Board approves unaudited quarterly financial results") == "financial_results"


def test_classifies_corporate_actions():
    assert classify_announcement("Company announces interim dividend") == "corporate_actions"


def test_extractive_summary_does_not_add_facts():
    content = "The company informed the Exchange about a board meeting."
    assert extractive_summary("Board meeting", content) == content
