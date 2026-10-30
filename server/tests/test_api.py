from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.api.routes import health, portfolio
from app.main import app

client = TestClient(app)


def test_root() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "running"


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_database_health(monkeypatch) -> None:
    monkeypatch.setattr(health, "check_database_connection", lambda: None)
    response = client.get("/health/db")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "connected"}


def test_empty_portfolio(monkeypatch) -> None:
    monkeypatch.setattr(portfolio, "list_portfolio", lambda db: [])
    response = client.get("/api/v1/portfolio")
    assert response.status_code == 200
    assert response.json() == []
