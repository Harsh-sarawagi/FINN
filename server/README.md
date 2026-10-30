# FINN Backend

FastAPI backend foundation for FINN.

## Setup

```powershell
cd server
Copy-Item .env.example .env
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Run

```powershell
python -m alembic -c alembic.ini upgrade head
python seed.py
python -m uvicorn app.main:app --reload
```

- API: http://127.0.0.1:8000
- Interactive docs: http://127.0.0.1:8000/docs
- Application health: http://127.0.0.1:8000/health
- Database health: http://127.0.0.1:8000/health/db

## Tests

```powershell
python -m pytest
```

## Structure

- `app/api/routes`: HTTP route modules.
- `app/config.py`: environment-backed application settings.
- `app/database`: SQLAlchemy engine, sessions, and connectivity check.
- `app/schemas`: API request/response models.
- `app/services`: application services without business-specific implementations yet.
- `tests`: FastAPI test coverage.

`/api/v1/portfolio` intentionally returns demo data and is not connected to a database. Live market data, AI features, FINN business logic, and product-specific database models are not implemented.
