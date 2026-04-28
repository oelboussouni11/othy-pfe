# Contributing to SmartLaunch QA

Thanks for working on this. This doc covers branching, commits, PRs, and local setup so we don't waste time on process.

---

## TL;DR

```bash
# One-time setup
make bootstrap

# Daily dev (3 terminals or use tmux/zellij)
make infra      # postgres + redis
make backend    # uvicorn on :8000
make frontend   # next dev on :3000

# Before pushing
make check      # lint + typecheck + tests
```

---

## Branching strategy

We use a simple **dev → main** flow:

```
feat/auth-login ──┐
fix/crawler-timeout ─┼──► dev ──► main (releases only)
chore/bump-deps ──┘
```

- **`main`** — production. Only updated via PR from `dev`. Tag releases here (`v1.0.0`).
- **`dev`** — integration branch. PRs from feature branches land here. Always green in CI.
- **Feature branches** — short-lived, named `<type>/<short-slug>`:
  - `feat/` new feature
  - `fix/` bug fix
  - `chore/` deps, tooling, refactors with no behavior change
  - `docs/` documentation only
  - `test/` test-only changes

Cut from `dev`, merge to `dev`. Don't branch from `main` unless it's a hotfix.

```bash
git checkout dev && git pull
git checkout -b feat/audit-rate-limit
# ... work ...
git push -u origin feat/audit-rate-limit
gh pr create --base dev
```

---

## Commit messages

[Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <imperative summary>

[optional body explaining the why, not the what]

[optional footer: refs #123, BREAKING CHANGE: ...]
```

- **type**: `feat`, `fix`, `chore`, `docs`, `test`, `refactor`, `perf`, `build`, `ci`
- **scope** *(optional)*: `backend`, `frontend`, `audit-engine`, `infra`, `auth`, `diff`, etc.
- **summary**: imperative, lowercase, no trailing period, ≤ 72 chars

Good:
```
feat(auth): add refresh token rotation
fix(crawler): respect robots.txt User-Agent specific rules
chore: bump next to 15.5.4 (CVE-2025-66478)
```

Bad:
```
updated stuff
WIP
fixed bug
```

One logical change per commit. If your PR has 8 commits and 5 are "wip", squash before review.

---

## Pull requests

1. **One PR = one concern.** Don't bundle a refactor with a feature unless it's required.
2. **Fill in the PR template.** Especially the test plan — describe what you actually clicked through.
3. **Link issues.** `Closes #42` in the PR body auto-closes on merge.
4. **CI must be green** before review.
5. **Get one approval** before merging to `dev`. Hot-fix exceptions only with explicit signoff.
6. **Squash-merge** to `dev` by default — keeps history readable. Merge commits only when preserving history matters (e.g. a feature that landed in many commits we want to keep).

### What reviewers look for
- Does it match the BUILD.md phase? (Don't ship Phase 5 logic in a Phase 3 PR.)
- Tests added/updated for the change.
- No new lint or type errors.
- No secrets, no `console.log`, no commented-out code.
- Migrations: forward AND backward (Alembic `downgrade`).

---

## Local development

### Prerequisites
- Python 3.12+ (3.14 works), Node 20+, Docker
- macOS, Linux, or WSL

### First-time setup
```bash
git clone <repo> && cd othy-pfe
cp .env.example .env
make bootstrap
```

`make bootstrap` does:
- Creates `backend/.venv` and installs Python deps
- `npm install` in `frontend/`
- Installs Playwright Chromium browser
- Pulls postgres + redis docker images

### Daily commands
| Command | What it does |
|---|---|
| `make infra` | Start postgres + redis (detached) |
| `make infra-down` | Stop postgres + redis |
| `make backend` | Run FastAPI on :8000 with reload |
| `make worker` | Run RQ worker (Phase 4+) |
| `make frontend` | Run Next.js on :3000 |
| `make test` | Run all tests (backend + audit_engine + frontend) |
| `make test-be` | Backend pytest only |
| `make test-fe` | Frontend Playwright only |
| `make lint` | Ruff + ESLint |
| `make fmt` | Auto-fix lint and format |
| `make typecheck` | Frontend TS typecheck |
| `make check` | lint + typecheck + tests (run before pushing) |
| `make migrate` | `alembic upgrade head` |
| `make migration name="add users table"` | Create new migration |
| `make clean` | Remove venv, node_modules, build artifacts |

---

## Code style

- **Python:** Ruff handles lint + format. Line length 100. Run `make fmt` before pushing.
- **TypeScript:** ESLint + Next config. Strict mode on. No `any` without a comment explaining why.
- **Imports:** Ruff auto-sorts (Python). Frontend uses `@/...` path aliases.
- **Comments:** Default to none. Add one only when the *why* is non-obvious. Don't restate the code.

---

## Adding a feature — end-to-end

1. **Pick a phase task** from `BUILD.md`. Don't skip ahead.
2. **Open an issue** if one doesn't exist. Use the feature template.
3. **Branch:** `git checkout -b feat/<slug>` from `dev`.
4. **Build:** small commits, conventional messages, tests in the same commit when possible.
5. **Run `make check` locally.**
6. **Open PR to `dev`.** Fill in the template.
7. **Address review.** Push more commits — don't force-push during review (makes diffs unreadable). Squash on merge.
8. **Merge.** Delete the branch.

When `dev` accumulates a phase's worth of changes and acceptance criteria are met, open a PR `dev → main` and tag a release.

---

## Project layout

See [BUILD.md §1](./BUILD.md#1-repository-structure) for the full tree. Key directories:
- `backend/app/api/` — FastAPI routers (one file per resource: `auth.py`, `projects.py`, ...)
- `backend/app/services/` — business logic. Routers stay thin.
- `backend/app/db/` — SQLAlchemy models + session
- `audit_engine/` — pure Python, no FastAPI imports. Worker calls it. Easy to test in isolation.
- `frontend/app/` — Next.js App Router pages
- `frontend/components/ui/` — shadcn primitives (don't hand-edit; use `npx shadcn add`)
- `frontend/components/` — your composed components
- `frontend/lib/` — utilities, API client

---

## Questions, blockers, decisions

- Architectural decisions go in `ARCHITECTURE.md` (short ADR-style entries).
- If something contradicts BUILD.md, surface it in the PR description, don't silently deviate.
- If you're stuck > 30 min, ping in the PR or open a draft PR with `[help wanted]`.
