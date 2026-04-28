#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

bold() { printf '\033[1m%s\033[0m\n' "$*"; }
info() { printf '  ▸ %s\n' "$*"; }

bold "1/4 .env"
if [ ! -f .env ]; then
  cp .env.example .env
  info "created .env from .env.example — review it"
else
  info ".env exists, skipping"
fi

bold "2/4 backend (Python venv + deps)"
cd backend
if [ ! -d .venv ]; then
  python3 -m venv .venv
  info "created backend/.venv"
fi
.venv/bin/pip install --upgrade --quiet pip
.venv/bin/pip install --quiet -r requirements.txt
info "backend deps installed"
cd "$ROOT"

bold "3/4 frontend (npm install + Playwright browsers)"
cd frontend
npm install --silent
info "frontend deps installed"
npx --yes playwright install chromium >/dev/null
info "Playwright Chromium installed"
cd "$ROOT"

bold "4/4 docker images"
docker compose pull --quiet
info "postgres + redis images pulled"

bold "Done."
echo
echo "Next:"
echo "  make infra       # start postgres + redis"
echo "  make backend     # run FastAPI on :8000"
echo "  make frontend    # run Next.js on :3000"
echo "  make test        # run all tests"
