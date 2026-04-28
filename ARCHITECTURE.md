# Architecture

A living document. Update it when you make a non-obvious decision, not when you write code.

---

## Components

```
┌──────────────┐      ┌──────────────┐
│  Next.js 15  │ ───► │   FastAPI    │
│  (frontend)  │ ◄─── │   (backend)  │
└──────────────┘      └──────┬───────┘
                             │
            ┌────────────────┼─────────────────┐
            ▼                ▼                 ▼
     ┌────────────┐   ┌────────────┐   ┌──────────────┐
     │ PostgreSQL │   │   Redis    │   │  RQ Worker   │
     │     18     │   │     7      │ ◄─┤ audit_engine │
     └────────────┘   └────────────┘   └──────────────┘
```

- **Frontend** (`frontend/`): Next.js App Router. Calls FastAPI over HTTP. Auth via httpOnly cookie.
- **Backend** (`backend/`): FastAPI + SQLAlchemy. Stateless. Enqueues audit jobs to Redis.
- **Worker** (`backend/app/workers/`): RQ consumer. Imports `audit_engine`, writes results to Postgres.
- **audit_engine** (`audit_engine/`): Pure Python. No FastAPI imports. Crawler + checks. Easy to test.
- **Postgres**: Source of truth. Users, projects, audits, issues, diffs.
- **Redis**: Job queue + (future) cache.

---

## Data flow — running an audit

1. User clicks "Run audit" → `POST /projects/{id}/audits`
2. Backend creates `Audit` row (status=`queued`), enqueues RQ job, returns `audit_id`
3. Worker picks up job, sets status=`running`
4. Worker invokes `audit_engine`:
   - crawl staging + production in parallel (if both URLs exist)
   - run link checks + SEO checks per environment
   - run diff
5. Worker writes `AuditIssue` and `AuditDiff` rows, sets status=`completed`
6. Frontend polls `GET /audits/{id}` every 2s while running, switches to result view on complete

---

## Boundaries we care about

- **`audit_engine` has no FastAPI / SQLAlchemy imports.** It's a library. The worker is the only thing that bridges DB and engine. This keeps the engine testable from a plain pytest, without spinning up the API.
- **Routers stay thin.** Business logic lives in `services/`. Routers do request validation → call service → shape response.
- **No DB queries in templates / components.** Frontend gets data via the API, period.

---

## Decisions (ADR-lite)

Format: short. If a decision is reversed, leave the entry but add a "Superseded by …" line.

### 2026-04 — Tailwind v3 (not v4) for Phase 1
Tailwind v4 is great but shadcn/ui's stable channel is still v3 in Apr 2026. Picking v3 keeps `npx shadcn add` smooth. Revisit when shadcn marks v4 stable.

### 2026-04 — Postgres 18 volume layout
Mount `postgres_data:/var/lib/postgresql` (not `/var/lib/postgresql/data`). Postgres 18 places data in a versioned subdir, and the `/data` mount triggers the "unused mount" check loop.

### 2026-04 — `dev → main` branching
See CONTRIBUTING.md. Keeps `main` deployable, gives us an integration branch for stacking multiple in-flight features.

<!-- New entries above this line. Keep them short. -->

---

## Open questions / risks

- **JS-rendered SPAs**: httpx-only crawler will miss client-rendered content. BUILD.md plans Playwright fallback for V2. Until then, document the limitation in audit reports.
- **Diff false positives from dynamic content**: timestamps, A/B-tested copy, CSRF tokens. Plan: per-project ignore-selector list (V2).
- **Audit fairness under load**: a single user could queue many audits and starve others. Phase 7 adds rate limiting; consider per-user concurrency cap if it bites earlier.
