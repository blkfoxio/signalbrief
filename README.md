# SignalBrief

Presales intelligence tool that converts prospect inputs into evidence-backed security narratives.

## Prerequisites

- Python 3.11+
- Node.js 18+
- npm

## Local Setup

### 1. Environment Variables

Copy the example and fill in your API keys:

```bash
cp .env.example .env
```

Required keys:
- `DEHASHED_API` — DeHashed v2 API key
- `OPENAI_API` — OpenAI API key
- `PROXYCURL_API` — Proxycurl API key

Optional (skip for local dev):
- `MS_AZURE_CLIENT_ID` / `MS_AZURE_SECRET` — Microsoft OAuth (use dev auth locally)

### 2. Backend (Django)

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 8000
```

The API runs at `http://127.0.0.1:8000`. Health check: `http://127.0.0.1:8000/api/health/`

### 3. Frontend (React)

In a **second terminal**:

```bash
cd frontend
npm install
npm run dev
```

The app runs at `http://localhost:5173`. The Vite dev server proxies `/api` requests to the Django backend.

### 4. First Login

1. Open `http://localhost:5173/login`
2. Use the **dev login** form (below the Microsoft button)
3. Click "Register" to create an account with email/password
4. You're in — create your first report

## Project Structure

```
signalbrief/
├── backend/           # Django REST API
│   ├── accounts/      # Auth (Microsoft OAuth + dev auth)
│   ├── companies/     # Company models + Proxycurl enrichment
│   ├── intelligence/  # DeHashed client + signal extraction + report orchestration
│   ├── narratives/    # OpenAI narrative generation
│   └── core/          # Shared models + utilities (masking, validators)
├── frontend/          # React + TypeScript + Vite + Tailwind
│   └── src/
│       ├── api/       # API client + endpoints
│       ├── auth/      # Auth context + protected routes
│       ├── pages/     # Dashboard, NewReport, Report, Login
│       └── components/# InputForm, NarrativeView, AuditPanel, etc.
└── .env.example       # Required environment variables
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health/` | Health check |
| GET | `/api/auth/login/` | Get Microsoft OAuth URL |
| POST | `/api/auth/callback/` | Exchange OAuth code for JWT |
| POST | `/api/auth/dev/register/` | Dev: register with email/password |
| POST | `/api/auth/dev/login/` | Dev: login with email/password |
| POST | `/api/auth/refresh/` | Refresh JWT token |
| GET | `/api/auth/me/` | Current user |
| POST | `/api/reports/` | Create new analysis report |
| GET | `/api/reports/` | List user's reports |
| GET | `/api/reports/{id}/` | Get report detail |
| GET | `/api/reports/{id}/raw/` | Get raw DeHashed data (masked) |

## Deployment (Railway)

The project deploys as two Railway services from the same repo:

- **Backend**: root directory `backend/`, uses `Procfile`
- **Frontend**: root directory `frontend/`, uses `nixpacks.toml`
- **Database**: Railway PostgreSQL addon (auto-injects `DATABASE_URL`)

Set `DJANGO_SETTINGS_MODULE=signalbrief.settings.production` in the backend service env vars.
