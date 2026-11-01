# FINN

FINN is a full-stack investment intelligence prototype built for the ENAM AI Engineer Build Challenge. It combines a Next.js responsive web frontend with a FastAPI and PostgreSQL backend.

## Implemented features

- Portfolio: add and remove NSE/BSE companies from the catalog.
- Market dashboard: refresh and view end-of-day prices, volume, daily changes, gainers, losers, and last-update status.
- Push intelligence: ingest NSE/BSE announcements, categorize them, create alert rules, view a daily digest, and mark alerts read.
- Pull research: search the company catalog, retrieve provider-reported financial periods, compare QoQ/YoY deterministically, calculate financial ratios, screen unusual patterns, and browse source-linked documents and guidance.
- AI research assistant: retrieve evidence from stored FINN data, link supporting sources, and optionally use OpenAI for explanation.
- Provider resilience: stored data remains available when external sources fail. Missing live data is labeled clearly rather than fabricated.

## Architecture

```text
Browser
  -> Next.js App Router UI
  -> NEXT_PUBLIC_API_BASE_URL
  -> FastAPI REST API
       -> SQLAlchemy / PostgreSQL
       -> yfinance and exchange announcement/document sources
       -> Optional OpenAI API
```

See HLD.md for module boundaries, data flow, provenance rules, and known limitations.

## Scheduled ingestion and live dashboard updates

- The backend scheduler is enabled with `SCHEDULER_ENABLED=true`.
- Market end-of-day data refreshes every `MARKET_INGESTION_INTERVAL_MINUTES` (default 60 minutes).
- NSE/BSE announcement refreshes every `ANNOUNCEMENT_INGESTION_INTERVAL_MINUTES` (default 30 minutes).
- PostgreSQL advisory locks prevent overlapping scheduler runs across API processes. Unique database constraints prevent duplicate market records, announcements, and alerts.
- Optional startup refresh can be enabled with `SCHEDULER_RUN_ON_STARTUP=true`.
- `/api/v1/events/stream` is an SSE endpoint for dashboard updates. It polls a PostgreSQL event outbox, so events survive API worker restarts and are not limited to one process.
- SSE sends heartbeats every `SSE_HEARTBEAT_SECONDS` seconds and supports browser reconnection via the standard `Last-Event-ID` mechanism.
- Market values remain end-of-day provider data; yfinance is not presented as real-time.

## Repository structure

```text
Enam_FINN/
├── finn-investment-agent/
│   ├── app/                 # App Router pages and layout
│   ├── components/          # Shared frontend components
│   └── lib/                 # API clients and shared frontend types
├── server/
│   ├── app/
│   │   ├── api/routes/      # FastAPI endpoints
│   │   ├── database/        # SQLAlchemy engine and sessions
│   │   ├── models/          # SQLAlchemy models
│   │   ├── schemas/         # API validation schemas
│   │   └── services/        # Provider, domain, and assistant services
│   ├── alembic/versions/    # Database migrations
│   └── tests/               # Backend pytest suite
├── HLD.md
└── README.md
```

## Prerequisites

- Node.js 20 or newer and npm
- Python 3.11 or newer
- PostgreSQL 14 or newer
- Internet access for optional live provider refreshes

## Environment configuration

### Backend

From server/, copy .env.example to .env and configure:

| Variable | Required | Purpose |
|---|---|---|
| DATABASE_URL | Yes | PostgreSQL connection string, for example `postgresql+psycopg://user:password@localhost:5432/finn` |
| CORS_ORIGINS | Yes | Comma-separated frontend origins |
| OPENAI_API_KEY | No | Enables assistant and announcement-summary interpretation |
| OPENAI_EMBEDDING_MODEL | No | Embedding model used for semantic document research; defaults to `text-embedding-3-small` |
| OPENAI_MODEL | No | Optional OpenAI model; defaults to a supported application default |
| AI_API_KEY | No | Groq or other OpenAI-compatible chat provider API key |
| AI_API_URL | No | OpenAI-compatible chat-completions URL; defaults to Groq when key is configured |
| AI_MODEL_NAME | No | Chat provider model, for example `openai/gpt-oss-120b` |
| ENVIRONMENT | No | Application environment label |

Never commit `.env`. Keep database credentials and API keys only in local or deployment secret stores.

### Frontend

From finn-investment-agent/, copy .env.example to .env.local. Configure:

```text
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

This value is embedded in the browser application, so it must not contain secrets.

## Local setup

### 1. Database and backend

```powershell
cd e:\Enam_FINN\server
Copy-Item .env.example .env
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m alembic -c alembic.ini upgrade head
python seed.py
python -m uvicorn app.main:app --reload
```

Backend documentation is available at http://127.0.0.1:8000/docs. Health checks are available at `/health` and `/health/db`.

### 2. Frontend

Open a second terminal:

```powershell
cd e:\Enam_FINN\finn-investment-agent
Copy-Item .env.example .env.local
npm install
npm run dev
```

FINN runs at http://localhost:3000.

## Demo workflow

1. Open `/portfolio` and add several catalog companies, for example TCS, INFY, and RELIANCE.
2. Open `/dashboard`, refresh market data, and review the live/fallback label and freshness timestamp.
3. Refresh intelligence from the dashboard and review categorized announcements, alert rules, digest, and read-state alerts.
4. Open `/research`, select a company, and review reported financial metrics, deterministic comparisons, documents, and guidance.
5. Ask the research assistant a supported question, then inspect source links, periods, basis, and document references.

The assistant ranks evidence within the selected company before sending it to the configured
OpenAI-compatible provider. Financial records are ranked by metric intent, announcements and
guidance use lexical relevance, and indexed document chunks combine keyword relevance with
optional embedding similarity when an OpenAI embedding key is configured. Groq chat providers
do not provide embeddings; FINN therefore remains fully searchable through keyword retrieval
when only Groq chat credentials are available.
6. Without an OpenAI key or provider access, repeat the workflow and confirm that FINN displays source-grounded fallback or unavailable states.

## Main API groups

| Area | Examples |
|---|---|
| Health | `GET /health`, `GET /health/db` |
| Portfolio | `GET/POST /api/v1/portfolio`, `DELETE /api/v1/portfolio/{ticker}` |
| Portfolio catalog/history | `GET /api/v1/companies?q=...`, `POST /api/v1/companies/discover`, `GET /api/v1/portfolio/history` |
| Market | `GET /api/v1/dashboard`, `POST /api/v1/market/sync`, `GET /api/v1/market/status` |
| Intelligence | `POST /api/v1/announcements/ingest`, `GET /api/v1/announcements`, `GET /api/v1/digest/daily`, `GET/POST /api/v1/alert-rules`, `GET /api/v1/alerts` |
| Research | `GET /api/v1/research/companies`, `POST /api/v1/research/sync`, `GET /api/v1/research/companies/{ticker}` |
| Assistant | `POST /api/v1/research/assistant/{ticker}` |

## Testing and validation

Backend:

```powershell
cd server
.\.venv\Scripts\python.exe -m pytest
python -m alembic -c alembic.ini current
```

Frontend:

```powershell
cd finn-investment-agent
npm run lint
npm run build
```

Run both applications simultaneously for frontend-to-backend verification.

## Deployment

For a small prototype deployment, run the Next.js frontend and FastAPI backend as separate services behind HTTPS.

- Deploy PostgreSQL with managed backups or a dedicated PostgreSQL instance.
- Set a production `DATABASE_URL` in a secret store.
- Set `CORS_ORIGINS` to the exact frontend HTTPS origin, comma-separated if multiple origins are required.
- Set `NEXT_PUBLIC_API_BASE_URL` to the public HTTPS backend origin at frontend build time.
- Store `OPENAI_API_KEY` only on the backend.
- Run `alembic upgrade head` before starting the API.
- Run the company seed once for an empty catalog; seed scripts should be safe to rerun.
- For larger deployments, use dedicated scheduler replicas or an external queue/worker service rather than relying on one in-process scheduler.

## Data provenance and limitations

- Market values are yfinance end-of-day values and may be unavailable or stale.
- NSE/BSE ingestion and document availability depend on external HTML/PDF endpoints.
- Research document embeddings and semantic cosine retrieval are available when OpenAI embeddings are configured. Embeddings are stored in PostgreSQL document-chunk rows; application-level cosine search is used because the verified PostgreSQL instance does not provide the `pgvector` extension.
- QoQ/YoY comparisons are calculated in Python; AI is not allowed to calculate them.
- OpenAI answers are based on FINN's retrieved evidence only. Missing sources, provider failures, and missing API keys produce explicit fallback messages.
- Financial provider units are preserved and are not automatically converted to INR.
- There is no authentication or user isolation in this prototype. Scheduled ingestion uses in-process workers with PostgreSQL overlap protection, and no external queue or production vector retrieval is configured.
- Portfolio removal deactivates membership only; company data and historical records are preserved. Removed memberships can be restored without creating a duplicate company or membership.

FINN must not be treated as investment advice.
