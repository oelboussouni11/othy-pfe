# SmartLaunch QA

Pre-launch website QA platform with staging vs production diff.

**Stack:** Next.js 15 · FastAPI · PostgreSQL 18 · Redis · RQ

See [BUILD.md](./BUILD.md) for the phased build plan.

## Quickstart (Phase 1)

```bash
cp .env.example .env

# Infrastructure
docker compose up -d

# Backend (terminal 1)
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend (terminal 2)
cd frontend
npm install
npm run dev
```

- Backend health: http://localhost:8000/health
- Frontend: http://localhost:3000

## Tests

```bash
# Backend
cd backend && pytest

# Frontend (Playwright)
cd frontend && npx playwright install chromium && npm run test:e2e
```
