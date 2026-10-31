#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# shellcheck disable=SC1091
source .venv/bin/activate
if [[ -f .env.runtime ]]; then
  # shellcheck disable=SC1091
  set -a; source .env.runtime; set +a
fi
export APP_PASSWORD="${APP_PASSWORD:-$(tr -d '\n' < .app_password)}"
export FLASK_SECRET_KEY="${FLASK_SECRET_KEY:-$(python3 -c 'import secrets; print(secrets.token_hex(16))')}"
pkill -f "waitress-serve .*server:app" 2>/dev/null || true
sleep 1
nohup env APP_PASSWORD="$APP_PASSWORD" FLASK_SECRET_KEY="$FLASK_SECRET_KEY" \
  .venv/bin/waitress-serve --host=0.0.0.0 --port=8600 server:app \
  > "$ROOT/mobile.log" 2>&1 &
echo "mobile pid=$!  log=$ROOT/mobile.log  url=http://127.0.0.1:8600"
