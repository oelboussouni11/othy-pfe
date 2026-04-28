# SmartLaunch QA — BUILD.md

**Project:** Pre-launch website QA platform with staging vs production diff
**Stack:** Next.js 15 + FastAPI + PostgreSQL 18 + Redis + RQ
**Path:** `~/Projects/SmartLaunchQA/`
**Approach:** Phased build. Each phase has tasks, acceptance criteria, and tests. Do NOT proceed to the next phase until all tests pass.

---

## 0. Ground Rules for Claude Code

1. **One phase at a time.** Stop after each phase, run its tests, report status, wait for approval.
2. **Test as you go.** Every endpoint, every audit check, every UI flow gets a test in the same phase it's built.
3. **Conventional commits.** `feat:`, `fix:`, `test:`, `chore:`, `docs:`. One logical change per commit.
4. **No skipping.** Do not jump ahead to "fancy" features. Diff staging/prod is the differentiator — protect it.
5. **Ask before deviating.** If the cahier des charges says X and reality demands Y, surface it before changing.
6. **Polite crawler.** Always respect `robots.txt`, throttle requests (max 5 concurrent per host), set a clear User-Agent: `SmartLaunchQA/1.0`.

---

## 1. Repository Structure

```
SmartLaunchQA/
├── frontend/                 # Next.js 15 App Router
│   ├── app/
│   ├── components/
│   ├── lib/
│   └── tests/                # Playwright E2E
├── backend/                  # FastAPI
│   ├── app/
│   │   ├── api/              # Routers
│   │   ├── core/             # Config, security
│   │   ├── db/               # SQLAlchemy models, session
│   │   ├── schemas/          # Pydantic
│   │   ├── services/         # Business logic
│   │   └── workers/          # RQ tasks
│   ├── alembic/
│   └── tests/                # pytest
├── audit_engine/             # Pure Python module, importable by worker
│   ├── crawler.py
│   ├── checks/
│   │   ├── links.py
│   │   ├── seo.py
│   │   └── diff.py
│   └── tests/
├── docker-compose.yml        # postgres + redis for local dev
├── .env.example
├── README.md
├── ARCHITECTURE.md
└── BUILD.md                  # this file
```

---

## Phase 1 — Project Setup & Skeleton (Week 1)

### Tasks
- [ ] `git init`, create GitHub repo, set up `main` + `dev` branches
- [ ] Create `docker-compose.yml` with `postgres:18` and `redis:7`
- [ ] Backend: scaffold FastAPI app with health endpoint `GET /health`
- [ ] Frontend: scaffold Next.js 15 with App Router, Tailwind, shadcn/ui
- [ ] `.env.example` with all needed vars (DB_URL, REDIS_URL, JWT_SECRET)
- [ ] Set up Alembic for migrations
- [ ] Set up pytest for backend, Playwright for frontend
- [ ] Add GitHub Actions: lint + tests on PR

### Acceptance Criteria
- `docker compose up` brings up postgres + redis without errors
- `curl http://localhost:8000/health` returns `{"status": "ok"}`
- `http://localhost:3000` shows a placeholder landing page
- `pytest` runs (with one dummy test passing)
- `npx playwright test` runs (with one dummy test passing)

### Tests
- `tests/test_health.py`: assert `/health` returns 200
- `tests/landing.spec.ts`: assert landing page loads

**STOP. Verify all green. Commit. Wait.**

---

## Phase 2 — Auth & User Management (Week 2)

### Tasks
- [ ] SQLAlchemy `User` model: `id, name, email, password_hash, role, created_at`
- [ ] Alembic migration for `users` table
- [ ] Argon2 password hashing (`argon2-cffi`)
- [ ] JWT access + refresh tokens (`pyjwt`)
- [ ] Endpoints: `POST /auth/register`, `POST /auth/login`, `POST /auth/refresh`, `GET /auth/me`
- [ ] Role enum: `admin`, `developer`, `pm`, `qa`
- [ ] FastAPI dependency `get_current_user` + role checker
- [ ] Frontend: login page, register page, auth context, protected route wrapper
- [ ] Persist tokens in httpOnly cookie (or secure storage)

### Acceptance Criteria
- Register → login → access `/auth/me` returns the user
- Wrong password returns 401
- Expired token returns 401, refresh issues new pair
- Frontend redirects unauthenticated users to `/login`

### Tests
- `test_auth.py`: register, login success/fail, refresh, role-protected route
- `auth.spec.ts`: register flow, login flow, redirect on logout

**STOP. Commit. Wait.**

---

## Phase 3 — Project Management (Week 3)

### Tasks
- [ ] `Project` model: `id, name, client_name, staging_url, production_url, status, owner_id, created_at`
- [ ] URL validation (must be valid HTTP/HTTPS)
- [ ] CRUD endpoints: `POST/GET/PATCH/DELETE /projects`
- [ ] Authorization: only owner or admin can edit/delete
- [ ] Frontend: projects list page, create project form, project detail page
- [ ] Empty state when no projects

### Acceptance Criteria
- User can create a project with both URLs (or just production)
- List view shows only the user's projects (admin sees all)
- Invalid URLs are rejected with clear error
- Editing another user's project returns 403

### Tests
- `test_projects.py`: create, list, get, update, delete, authorization
- `projects.spec.ts`: full CRUD flow in UI

**STOP. Commit. Wait.**

---

## Phase 4 — Audit Engine Core (Weeks 4–6)

This is the **biggest phase**. Build the engine as a standalone Python module first, then plug it into the worker.

### 4.1 Crawler
- [ ] `audit_engine/crawler.py`: async crawler using `httpx.AsyncClient`
- [ ] Inputs: seed URL OR sitemap.xml URL
- [ ] Respects `robots.txt` (use `urllib.robotparser`)
- [ ] Max concurrency: 5 per host (`asyncio.Semaphore`)
- [ ] Per-request timeout: 10s
- [ ] Retry once on network errors
- [ ] Same-origin only by default
- [ ] Returns: list of `CrawledPage(url, status_code, html, response_time_ms)`

**Tests:** crawl a local fixture site (use `pytest-httpserver`), assert all pages found.

### 4.2 Link & HTTP Audit
- [ ] `checks/links.py`: extract `<a href>`, classify by status code
- [ ] Map: 200 → ok, 301 → info, 302 → warn, 4xx/5xx → critical
- [ ] Detect redirect chains (>2 hops = warn)

**Tests:** fixture site with deliberate broken links → all caught.

### 4.3 SEO Audit
- [ ] `checks/seo.py` checks per page:
  - `<title>` exists, length 30–65 chars
  - `<meta name="description">` exists, length 70–160 chars
  - Exactly one `<h1>`
  - `<link rel="canonical">` present
  - Open Graph: `og:title`, `og:description`, `og:image`
  - All `<img>` have non-empty `alt`
- [ ] Each issue: `{page_url, type, severity, message, recommendation}`

**Tests:** fixture pages for each SEO violation → each detected with correct severity.

### 4.4 Worker Wiring
- [ ] `backend/app/workers/audit_task.py`: RQ task that runs the engine and writes to DB
- [ ] `Audit` model: `id, project_id, environment, status, started_at, finished_at, seo_score, broken_links_count`
- [ ] `AuditIssue` model: `id, audit_id, page_url, type, severity, message, recommendation, status_code`
- [ ] Endpoint `POST /projects/{id}/audits` enqueues the job
- [ ] Endpoint `GET /audits/{id}` returns status + results
- [ ] Status lifecycle: `queued → running → completed | failed`

### Acceptance Criteria
- Run an audit against a real site (e.g. `example.com`) — completes within 60s
- 50-page test site finishes in under 3 minutes (per cahier des charges §16)
- Issues correctly persisted, linked to audit
- Crashed worker job marks audit as `failed`, not stuck on `running`

### Tests
- `test_crawler.py`, `test_links.py`, `test_seo.py` — unit tests on fixtures
- `test_audit_integration.py`: full enqueue → run → fetch results
- 100% broken-link detection on prepared test site

**STOP. Commit. Wait.**

---

## Phase 5 — Diff Staging vs Production (Weeks 7–8)

**The differentiator. Protect this phase. Do not cut corners.**

### Tasks
- [ ] `checks/diff.py` — runs after both environments are crawled
- [ ] `AuditDiff` model: `id, audit_id, page_url, field, staging_value, production_value, change_type`
- [ ] Diff categories:
  - **Pages:** present in staging only / production only
  - **SEO tags:** title, meta description, h1, canonical changed
  - **HTTP regressions:** was 200 in staging, now 4xx/5xx in production
  - **Internal links:** worked in staging, broken in production
  - **Open Graph:** og tags changed or removed
- [ ] URL normalization: align staging/prod paths (strip domain, normalize trailing slashes)
- [ ] **Go/No-Go verdict logic:**
  - No-Go if any production page returns 4xx/5xx that worked in staging
  - No-Go if production is missing pages that exist in staging
  - Go otherwise (warnings allowed)
- [ ] Endpoint `GET /audits/{id}/diff` returns structured diff + verdict
- [ ] When project has both URLs, audit auto-runs on both environments in parallel

### Acceptance Criteria
- Test scenario: staging has 10 pages, production has 9 → diff catches missing page → No-Go
- Test scenario: title changed between envs → diff flags it as warning, still Go
- Test scenario: link worked in staging, 404 in prod → No-Go
- Verdict reasoning is human-readable (list of triggering issues)

### Tests
- `test_diff.py`: 5+ regression scenarios from cahier des charges §16
- Each diff category has at least one positive + one negative test case

**STOP. Commit. Wait.**

---

## Phase 6 — Frontend Dashboard (Weeks 9–11)

### Tasks
- [ ] **Projects page:** list with quick stats (last audit verdict, date)
- [ ] **Project detail page:**
  - Header: name, URLs, last verdict badge
  - "Run new audit" button
  - Audits history table (date, duration, verdict, score)
- [ ] **Audit detail page:**
  - Summary card: pages crawled, broken links, SEO score, verdict
  - Tabs: `Issues` | `Diff` | `Pages`
  - Issues view: filter by severity, type, environment
  - Diff view: side-by-side staging vs production for changed fields
  - Pages view: full crawl table with statuses
- [ ] **Status polling:** for running audits, poll `/audits/{id}` every 2s, update UI live
- [ ] **Verdict badge:** large, color-coded (green Go / red No-Go), with reasoning expandable
- [ ] **Export HTML:** server-side endpoint `GET /audits/{id}/export.html` — standalone styled report
- [ ] Responsive (works on tablet at minimum)

### Design notes
- Clean, professional, not flashy — this is a serious tool for PMs
- Severity colors: critical=red, warning=amber, info=blue, ok=green
- Use shadcn/ui Table, Badge, Card, Tabs, Dialog

### Acceptance Criteria
- A non-technical PM can understand a verdict without help (cahier des charges §16)
- Live polling never reloads the whole page
- HTML export opens correctly in any browser, contains all data

### Tests
- `audit_flow.spec.ts` (Playwright): create project → run audit → see results → view diff → export
- Component tests for Verdict badge, Issue row, Diff row

**STOP. Commit. Wait.**

---

## Phase 7 — Testing, Hardening, Real-World Validation (Weeks 12–13)

### Tasks
- [ ] Test coverage: backend ≥ 80%, audit_engine ≥ 90%
- [ ] 3+ end-to-end Playwright scenarios covering happy path + 1 failure path
- [ ] Rate limiting on `POST /projects/{id}/audits` (max 5/hour per user)
- [ ] CORS strict (whitelist frontend origin only)
- [ ] Sentry integration on backend + frontend
- [ ] Structured JSON logging (one line per request, with audit_id when relevant)
- [ ] Run audit against a **real Webloo client site** — collect feedback
- [ ] Performance check: 50-page site in under 3 minutes (cahier des charges §16)
- [ ] Security review: SQL injection (SQLAlchemy params), XSS in HTML export (escape user content), JWT expiry, password reset flow if added

### Acceptance Criteria
- Full test suite passes in CI
- Real Webloo audit completed, feedback documented in `WEBLOO_FEEDBACK.md`
- No critical Sentry errors in 24h of dogfooding
- All success criteria from cahier des charges §16 met

### Tests
- Coverage report committed
- Load test: 10 concurrent audits don't crash worker

**STOP. Commit. Wait.**

---

## Phase 8 — Deployment & Documentation (Weeks 14–15)

### Tasks
- [ ] Frontend → Vercel (production + preview branches)
- [ ] Backend API → Render or Railway
- [ ] Worker → same host as API (separate service)
- [ ] PostgreSQL → managed (Render Postgres or Neon)
- [ ] Redis → managed (Upstash)
- [ ] Production env vars set + secrets rotated
- [ ] Custom domain (if Webloo provides one)
- [ ] `README.md`: quickstart, env vars, local dev
- [ ] `ARCHITECTURE.md`: components, data flow diagram, decisions
- [ ] OpenAPI spec auto-published at `/docs`
- [ ] Demo video (3–5 min) — full audit flow with diff
- [ ] PFE report (separate document)
- [ ] Soutenance slides

### Acceptance Criteria
- Production URL is live, anyone with credentials can run an audit
- Cold start to first audit result < 90s
- Documentation lets a new dev run the project locally in <15 min

**STOP. Final commit. Tag `v1.0.0`.**

---

## Testing Strategy Summary

| Layer | Tool | Coverage Target |
|-------|------|-----------------|
| Audit engine | pytest + fixtures | ≥ 90% |
| FastAPI endpoints | pytest + httpx TestClient | ≥ 80% |
| Background jobs | pytest-rq or fakeredis | All happy + failure paths |
| Frontend components | Vitest + React Testing Library | Critical components only |
| End-to-end | Playwright | 3+ scenarios |

**Test fixtures live in `audit_engine/tests/fixtures/` as static HTML files** — predictable, fast, no network.

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| JS-rendered sites break crawler | Default to httpx; add Playwright fallback only when `<noscript>` heuristic detects SPA |
| Worker queue backs up | Cap concurrent audits per user; show queue position in UI |
| Diff false positives from dynamic content | Allow user to define "ignore selectors" per project (Phase V2) |
| Webloo dev rejects the tool | Run real audit early (Phase 7), iterate on feedback before soutenance |

---

## V2 Backlog (Out of Scope for MVP)

- Lighthouse score integration
- Full a11y audit (axe-core)
- PDF export
- ClickUp / GitHub integration
- Continuous post-launch monitoring
- Visual regression screenshots

---

## How to Run Locally

```bash
# Clone
git clone <repo> && cd SmartLaunchQA

# Infrastructure
docker compose up -d

# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload

# Worker (separate terminal)
rq worker audits

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

---

**Now starting at Phase 1.**
