#!/usr/bin/env bash
# 尽量用 cloudflared 开临时公网链接；当前 Grok Bot 云电脑出口可能拦边缘握手，失败属已知限制。
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CF="${HOME}/bin/cloudflared"
[[ -x "$CF" ]] || CF="$(command -v cloudflared || true)"
if [[ -z "${CF}" ]]; then
  echo "cloudflared not found; put binary at ~/bin/cloudflared" >&2
  exit 1
fi
pkill -f "cloudflared tunnel --url" 2>/dev/null || true
sleep 1
: > "$ROOT/cloudflared.log"
nohup env GODEBUG=tlsmlkem=0 "$CF" tunnel --url http://127.0.0.1:8600 --protocol http2 \
  > "$ROOT/cloudflared.log" 2>&1 &
echo "cloudflared pid=$!"
for i in $(seq 1 20); do
  URL=$(grep -oE 'https://[a-zA-Z0-9.-]+\.trycloudflare\.com' "$ROOT/cloudflared.log" | head -1 || true)
  if [[ -n "${URL}" ]]; then
    echo "URL=$URL"
    echo "(若 curl 返回 530，说明边缘未连上，见 README 已知限制)"
    exit 0
  fi
  sleep 1
done
echo "no URL yet; see $ROOT/cloudflared.log" >&2
exit 1
