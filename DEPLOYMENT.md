# FINN free deployment

This deployment uses Vercel, Render Free Web Service, and Neon Free/PostgreSQL.

## 1. Create the Neon database

1. Create a Neon project and database.
2. Copy its pooled PostgreSQL connection URL.
3. Ensure the URL contains `sslmode=require`. Neon connection strings usually use `postgresql://`.

## 2. Deploy FastAPI on Render

1. Create a new Render Blueprint from this repository and select `server/render.yaml`.
2. Add these secret values in the Render service:
   - `DATABASE_URL`
   - `CORS_ORIGINS`
   - optional Groq/OpenAI values: `AI_API_KEY`, `AI_API_URL`, and `AI_MODEL_NAME`
3. Deploy with the Render root directory set to `server`.
4. Confirm Render runs migrations before starting the application.
5. Verify:
   - `https://<service>.onrender.com/health`
   - `https://<service>.onrender.com/health/db`
   - `https://<service>.onrender.com/docs`

The free Render service sleeps after inactivity. The first request can take time to wake the service, and SSE connections will disconnect when Render restarts or sleeps. FINN uses EventSource, which reconnects automatically, but live updates should be treated as best-effort in the free tier.

## 3. Deploy Next.js on Vercel

1. Import the repository in Vercel.
2. Set the project root directory to `finn-investment-agent`.
3. Add `NEXT_PUBLIC_API_BASE_URL=https://<service>.onrender.com`.
4. Deploy.
5. Set Render's `CORS_ORIGINS` to the exact Vercel production origin, for example:
   `https://finn.vercel.app`
6. Redeploy the backend and frontend if origins or API URLs change.

Preview deployments use generated Vercel URLs. Add each required preview origin explicitly if preview deployments need API access.

## 4. Database migrations

Render's `preDeployCommand` runs the migrations automatically. For a manual migration:

```powershell
cd server
$env:DATABASE_URL="postgresql://USER:PASSWORD@HOST/DATABASE?sslmode=require"
python -m alembic -c alembic.ini upgrade head
```

Do not commit the Neon connection string. Review the applied migrations before resetting a non-empty database:

```powershell
python -m alembic -c alembic.ini current
python -m alembic -c alembic.ini history
```

## 5. Scheduled ingestion

The APScheduler is disabled by default in production because Render Free restarts and sleeping do not provide reliable recurring execution. Use manual refresh or a free external HTTPS scheduler when needed.

FINN currently exposes these refresh operations:

- `POST /api/v1/market/sync`
- `POST /api/v1/announcements/ingest`

They wake Render when invoked externally, but scheduled execution is not guaranteed across free-tier sleep and restart intervals. Add authentication before exposing a protected ingestion automation endpoint publicly.
