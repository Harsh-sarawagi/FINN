# FINN Investment Agent Frontend

Responsive Next.js frontend for FINN using the App Router, TypeScript, and Tailwind CSS.

## Setup

```powershell
Copy-Item .env.example .env.local
npm install
npm run dev
```

The application runs at http://localhost:3000. It uses `NEXT_PUBLIC_API_BASE_URL` to locate the FastAPI backend; the default is http://127.0.0.1:8000.

## Available scripts

```powershell
npm run dev
npm run build
npm run start
npm run lint
```

The reusable API client is in `lib/api-client.ts`. The App Router structure is unchanged and is ready for backend integration without placeholder product functionality.
