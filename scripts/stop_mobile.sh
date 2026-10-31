#!/usr/bin/env bash
pkill -f "waitress-serve .*server:app" 2>/dev/null || true
pkill -f "cloudflared tunnel --url" 2>/dev/null || true
pkill -f "localtunnel --port 8600" 2>/dev/null || true
echo "stopped mobile app / tunnels (if any)"
