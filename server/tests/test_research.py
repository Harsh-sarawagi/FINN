from app.services.research import percentage_change


def test_percentage_change_calculation():
    assert percentage_change(110, 100) == 10.0


def test_percentage_change_handles_missing_prior():
    assert percentage_change(110, None) is None


def test_percentage_change_handles_zero_prior():
    assert percentage_change(110, 0) is None
