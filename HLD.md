# FINN — Basic High-Level Design

## 1. Purpose and status

This document describes the technical foundation currently present in the FINN repository and the likely architecture for future work. It is intentionally high level. FINN product requirements and detailed business rules are placeholders and will be defined in later stages.

**Implemented now** means the repository already contains the component or configuration described. **Proposed** means it is a planned direction, not an implemented feature.

FINN is an AI-powered mobile-first financial investment agent for the ENAM AI Engineer Build Challenge. The challenge describes two broad interaction modes:

- **Push:** proactively show relevant changes, digests, and configurable alerts.
- **Pull:** support on-demand company research and analysis.

The detailed product workflows and prioritisation rules remain open placeholders.

## 2. Current repository structure

| Area | Current location | Current state |
|---|---|---|
| Frontend | `finn-investment-agent/` | Next.js application created with the App Router, TypeScript, React, and Tailwind CSS. |
| Backend | `server/` | FastAPI application with health/root endpoints and a demo portfolio endpoint. |
| Backend environment | `server/.venv/` | Local Python virtual environment is present. |
| Backend dependencies | `server/requirements.txt` | Python dependencies are declared and installed locally. |
| Backend environment template | `server/.env.example` | Example values for CORS, database, and OpenAI configuration. |
| Challenge brief | `1. ENAM... (1).pdf` | Product and challenge requirements reference used for this document. |

## 3. Frontend foundation

### Implemented

- Next.js 16.4.3 using the App Router.
- React 19.3.0 and TypeScript 5 in strict mode.
- Tailwind CSS 4 with global theme styles.
- Development, build, start, and lint scripts in `package.json`.
- Default generated home page and root layout are still present.
- No application-specific FINN workflows, navigation, state management, API client, or deployed frontend configuration exist yet.

The frontend can be run locally with `npm run dev` from `finn-investment-agent/`.

### Responsibilities

The proposed frontend responsibilities are:

- Mobile-first presentation of FINN information.
- Push-oriented views such as digests, notifications, and alerts.
- Pull-oriented company research views and interactions.
- Loading, empty, error, and source/citation presentation for future API responses.
- A responsive interaction model; the preferred final interaction pattern is not yet decided.

Specific pages, components, interaction patterns, visual design, and business workflows are proposed placeholders and are not implemented yet.

## 4. Backend foundation

### Implemented

- FastAPI application is defined in `server/main.py`.
- Root and health endpoints are available.
- A versioned demo portfolio endpoint is available at `/api/v1/portfolio`.
- The demo portfolio response is explicitly marked with `is_demo_data: true`.
- CORS is configured through `CORS_ORIGINS`, with localhost frontend origins as defaults.
- Interactive API documentation is available through FastAPI `/docs` when the server is running.
- Modular API routes, configuration, schemas, services, database helpers, and tests are implemented; PostgreSQL connectivity is tested independently through `/health/db`.

The backend can be started locally with:

```text
python -m uvicorn main:app --reload
```

from the `server/` directory.

### Proposed responsibilities

The backend is expected to be the integration boundary for future functionality:

- REST API endpoints for frontend features.
- Portfolio and watchlist management.
- Digest and alert request handling.
- Company research orchestration.
- Data ingestion, validation, caching, and source-reference handling.
- AI model orchestration and service integrations.
- Authentication and authorization when required.
- Database and external-provider access behind the API layer.

The exact routes, schemas, service boundaries, and authentication approach are undecided.

## 5. Frontend/backend communication

The proposed communication path is:

```text
Browser / mobile responsive frontend
            |
            | HTTPS / JSON REST calls
            v
FastAPI backend
            |
            +--> Database
            +--> Market-data providers
            +--> Announcement and filing sources
            +--> Fundamental-document sources
            +--> AI model providers
```

- Frontend requests should use a configurable backend base URL rather than hard-coded production addresses.
- JSON should be the primary API format.
- The backend should enforce validation and keep provider credentials and API keys out of the browser.
- Existing localhost CORS values support local frontend development.
- Production CORS, versioning conventions beyond the existing `/api/v1` example, error formats, pagination, streaming, and authentication are undecided.

## 6. Proposed high-level architecture

```text
+-----------------------------+
| Next.js Web Application     |
| Mobile-first UI             |
+-------------+---------------+
              |
+-------------v---------------+
| FastAPI API Service         |
| API, orchestration, validation |
+------+-----+-----+-----+----+
       |     |     |     |
       |     |     |     +--> AI Provider
       |     |     +--------> Filing/Announcement Sources
       |     +--------------> Fundamental Document Sources
       +--------------------> Market Price/Volume Sources
                                  |
                              +---v---+
                              | Database |
                              +---------+
```

This can remain a modular monolith initially; separate services are proposed only if scale, isolation, or asynchronous processing requirements justify them later.

## 7. Database role

SQLAlchemy and Alembic are included in the Python dependencies, and `DATABASE_URL` is present in the backend environment example. SQLAlchemy engine/session management and a PostgreSQL connectivity check are now implemented in `app/database/connection.py`; a live PostgreSQL server is required for `/health/db` to return connected.

The initial PostgreSQL foundation now includes `companies` and `portfolio_members` models, with an Alembic migration. The database catalog contains 20 NSE seed companies and includes the existing demo portfolio in the seeded portfolio table.

When implemented, the database may store:

- Application configuration and future user preferences.
- Portfolio and watchlist records.
- Cached market and announcement data.
- Ingestion state and source metadata.
- Research results, summaries, citations, and alert history.

The initial entities, constraints, and migration policy are implemented for companies, portfolio membership, daily market prices, and market synchronization status. Market prices are keyed by company and trading date, while synchronization status records provider attempts and freshness. Future domain entities, retention periods, and caching strategy remain undecided. Portfolio APIs now read and update PostgreSQL; the endpoint no longer returns static demo data.

Phase 2 uses yfinance to fetch recent NSE/BSE end-of-day history for portfolio companies. Daily OHLC/volume records are stored in PostgreSQL and the dashboard derives latest/previous close changes, gainers, losers, portfolio averages, and provider freshness from those records. Missing provider records and failed synchronization attempts are handled as non-live fallback states in the API and UI. Background refresh is enabled by a FastAPI scheduler with configurable market and announcement intervals; provider data remains end-of-day rather than real-time.

**Phase 3 — Push Intelligence (implemented foundation):** Portfolio companies are ingested through the NSE corporate-announcements API. `announcements` stores source URLs, publication time, company reference, category, ingestion status, fingerprint, summary provenance, and demo/live provenance. Alert rules can match categories and companies; alerts use a unique rule/announcement constraint to prevent duplicate notifications. Optional OpenAI text summarization is constrained to supplied announcement content; when no key/provider response is available, FINN stores an extractive fallback and labels the summary as not AI-generated. A daily digest and dashboard filters are based on stored announcements. **Phase 4 — Pull Research (implemented foundation):** Company lookup searches the PostgreSQL catalog and can resolve an uncatalogued NSE/BSE ticker through yfinance. Pull research stores provider-reported quarterly Revenue, EBITDA, PBT, and PAT values with reporting period, basis, units, and source provenance. QoQ and YoY percentages are calculated deterministically in FINN and are not provider-generated values. NSE documents discovered through stored corporate announcements populate the research document library. The guidance entity remains separate from reported results. **Phase 5 — AI Research Assistant (implemented foundation):** `/api/v1/research/assistant/{ticker}` retrieves stored reported financials, announcements, management guidance, and extractable PDF document text using deterministic keyword matching. Retrieved financial comparisons remain calculated in Python. Citation records preserve source URL, source name, reporting period, basis, and document reference where available. OpenAI is optional and is used only for explanation when `OPENAI_API_KEY` is configured; otherwise FINN returns a source-grounded fallback. Unsupported questions, unavailable documents, provider failures, and missing API credentials are handled explicitly and are not presented as facts.

## 8. External APIs and data sources

The challenge brief identifies several future capability areas. They are placeholders until providers and extraction workflows are selected and implemented.

### Implemented

`yfinance` is currently integrated for NSE/BSE end-of-day market-price data. NSE corporate announcements are integrated for portfolio-company ingestion. Other declared market and document libraries are not yet provider integrations:

- `requests` and `httpx` for possible source access.
- `BeautifulSoup`, `lxml`, and `PyMuPDF` for possible document and web processing.
- `pandas`, `numpy`, and Python standard data tooling for possible analysis.
- `openai` for possible AI-provider integration.

### Proposed integrations

- **Price and volume:** implemented as a user-triggered yfinance ingestion of recent NSE/BSE end-of-day OHLC and volume for Phase 2 portfolio metrics. Scheduled refresh, corporate-action handling, provider SLA, and configurable alerts remain undecided.
- **Corporate announcements and filings:** source and classification data for portfolio stocks and the digest workflow.
- **Company fundamentals:** provider-reported quarterly financials and source-linked documents derived from NSE/BSE announcements for on-demand research. Guidance extraction and complete transcript/document coverage remain limited.
- **AI services:** extraction, summarisation, classification, comparison, and research synthesis using cost-conscious model routing.
- **Optional profile enrichment:** professional background for named management contacts, where used only in the push workflow.

External providers, API availability, scraping compliance, rate limits, licensing, data freshness, reliability, and fallback behaviour are undecided.

## 9. Challenge functionality placeholders

The challenge asks for FINN product capabilities, but these are deliberately not defined as detailed business logic at this stage.

### Push placeholders

- **Windowed portfolio digest:** `[TO BE DESIGNED]`
- **Configurable portfolio filing filters and priorities:** `[TO BE DESIGNED]`
- **Material-announcement alerts:** `[TO BE DESIGNED]`
- **Unusual price/volume alerts:** `[TO BE DESIGNED]`
- **Configurable alert thresholds:** `[TO BE DESIGNED]`
- **Announcement summaries and source links:** `[TO BE DESIGNED]`
- **Management-change enrichment:** `[TO BE DESIGNED]`
- **Results extraction, including Revenue, EBITDA, PBT, PAT and QoQ/YoY comparisons:** `[TO BE DESIGNED]`

### Pull placeholders

- **Company lookup for any available NSE ticker:** `[TO BE DESIGNED]`
- **Business snapshot:** `[TO BE DESIGNED]`
- **Financial snapshot:** `[TO BE DESIGNED]`
- **Trajectory / multi-year analysis:** `[TO BE DESIGNED]`
- **Balance sheet and leverage analysis:** `[TO BE DESIGNED]`
- **Cash-flow quality analysis:** `[TO BE DESIGNED]`
- **Narrative versus numbers analysis:** `[TO BE DESIGNED]`
- **Management guidance extraction:** `[TO BE DESIGNED]`
- **Bull versus bear case:** `[TO BE DESIGNED]`
- **Primary-source grounding from annual reports and transcripts:** `[TO BE DESIGNED]`

### Interaction placeholders

- **Interaction model:** Chat, dashboard, copilot, voice, or a combination is undecided.
- **Mobile-first layout and navigation:** `[TO BE DESIGNED]`
- **Portfolio and ad-hoc research selections:** `[TO BE DESIGNED]`

## 10. Environment configuration

### Frontend

A frontend environment convention is not yet configured. Any public backend URL or feature flags should be added through Next.js environment variables if needed.

### Backend

The backend example defines:

| Variable | Purpose | Current status |
|---|---|---|
| `CORS_ORIGINS` | Allowed frontend origins for local development | Implemented in `server/main.py` with localhost defaults. |
| `DATABASE_URL` | PostgreSQL connection string | Configured for SQLAlchemy; connectivity depends on a running PostgreSQL instance. |
| `OPENAI_API_KEY` | Future OpenAI provider credential | Placeholder only. |
| `OPENAI_MODEL` | Future model selection | Placeholder only. |

Secrets must remain on the backend and must not be committed. The final provider, runtime settings, secret-management approach, and deployment-specific configuration are undecided.

## 11. Possible deployment structure

### Local development

- Next.js development server: normally `http://localhost:3000`.
- FastAPI development server with Uvicorn: normally `http://127.0.0.1:8000`.
- Separate processes and localhost CORS configuration.
- Backend virtual environment: `server/.venv/`.

### Proposed prototype deployment

- Deploy the Next.js frontend to a suitable static or managed Next.js platform.
- Deploy the FastAPI backend as a managed Python service, container, or platform-native process.
- Add environment-specific API URLs and CORS origins.
- Provision the selected database and migrations when persistence is required.
- Store secrets using the deployment platform's secret manager.
- Add health/readiness monitoring and provider credentials only when those integrations are implemented.

The final hosting providers, domains, CI/CD, containers, database service, observability, and scaling approach are undecided.

## 12. Current implementation boundaries

FINN currently has:

- A Next.js App Router frontend with responsive portfolio, dashboard, and research navigation.
- A modular FastAPI service with health, portfolio, market, intelligence, research, and assistant routes.
- Reusable frontend API clients driven by `NEXT_PUBLIC_API_BASE_URL`.
- SQLAlchemy PostgreSQL connection management, migrations, seeds, and connectivity checks.
- Portfolio, market, announcement, alert, research, document, guidance, and assistant data models.
- Optional provider and AI integrations with explicit stored-data and source-grounded fallbacks.
- Backend tests and frontend lint/build validation.

Authentication and user isolation remain outside the current prototype scope. Ingestion runs in-process scheduler workers protected by PostgreSQL advisory locks; production multi-instance scaling and external queue infrastructure may be added later. Production vector search and hosted deployment configuration remain outside the current prototype scope.

## 13. Final integration status

**Phase 6 — Final Integration (implemented for the prototype):** FINN modules are integrated through shared App Router navigation and a single FastAPI REST boundary. The dashboard aggregates portfolio market data, announcements, the daily digest, alert rules, and alerts while preserving module-level fallback behavior when a provider is unavailable. Portfolio and research pages expose loading, empty, validation, and provider-error states. Data labels distinguish live provider data, stored demo/fallback data, deterministic derived calculations, and optional AI-generated output. OpenAI is an optional backend credential and provider outage does not prevent source-grounded fallback responses. Authentication, scheduled background ingestion, production vector retrieval, and horizontally scaled services remain outside the current prototype scope.

The implemented product walk is: catalog/portfolio -> market refresh -> announcement ingestion and alerts -> company research -> source-grounded AI question. PostgreSQL is the durable store; provider and AI integrations remain replaceable service boundaries.

## 14. Updating this document

When implementation progresses, update this document by:

1. Moving items from **Proposed** or `[TO BE DESIGNED]` to **Implemented** with precise file references.
2. Recording the selected database and external providers.
3. Documenting final API boundaries and authentication.
4. Adding the chosen deployment and environment topology.
5. Replacing placeholders with concise, stable architectural descriptions without adding detailed business rules here.
