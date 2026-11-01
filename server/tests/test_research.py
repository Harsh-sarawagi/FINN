from app.services.research import percentage_change
from app.services.research_analytics import robust_z


def test_percentage_change_calculation():
    assert percentage_change(110, 100) == 10.0


def test_percentage_change_handles_missing_prior():
    assert percentage_change(110, None) is None


def test_percentage_change_handles_zero_prior():
    assert percentage_change(110, 0) is None


def test_robust_z_requires_history():
    score = robust_z([10, 11, 10])
    assert score is not None
    assert abs(score) < 1
