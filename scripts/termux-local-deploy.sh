#!/data/data/com.termux/files/usr/bin/env bash
# =============================================================================
# Git-Fix local deployment for Termux (Android)
# =============================================================================
# Bare-metal deploy without Docker: Flask backend (sqlite memory store) on
# :5000 + Vite dev server on :5173 (proxies /api and /ws to the backend).
#
# Usage:
#   scripts/termux-local-deploy.sh start     # start backend + frontend
#   scripts/termux-local-deploy.sh stop      # stop both
#   scripts/termux-local-deploy.sh status    # show pids + health
# =============================================================================
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_PORT="${GITFIX_PORT:-5000}"
FRONTEND_PORT="${GITFIX_FRONTEND_PORT:-5173}"
FEATURE_WEBSOCKET="${FEATURE_WEBSOCKET:-true}"
BACKEND_LOG="$REPO/logs/backend-local.log"
FRONTEND_LOG="$REPO/logs/frontend-local.log"
PIDFILE_BACKEND="$REPO/logs/backend-local.pid"
PIDFILE_FRONTEND="$REPO/logs/frontend-local.pid"
MEMDIR="$HOME/.gitfix/memory"

cmd_start() {
  mkdir -p "$REPO/logs" "$MEMDIR"

  # ---- Backend: python3 -m backend.app (run as package from repo root) ----
  if [ -f "$PIDFILE_BACKEND" ] && kill -0 "$(cat "$PIDFILE_BACKEND")" 2>/dev/null; then
    echo "backend already running (pid $(cat "$PIDFILE_BACKEND"))"
  else
    echo "starting backend on :${BACKEND_PORT} ..."
    # DB + auth from repo .env (load_env never overrides real env), but keep
    # DATABASE_URL pinned to the local sqlite memory store for Termux.
    DATABASE_URL="sqlite:///$MEMDIR/memory.db" \
    FLASK_DEBUG=false \
    PORT="$BACKEND_PORT" \
    GITFIX_BG_WORKERS="${GITFIX_BG_WORKERS:-4}" \
      setsid nohup python3 -m backend.app \
        > "$BACKEND_LOG" 2>&1 < /dev/null &
    echo $! > "$PIDFILE_BACKEND"
    for _ in $(seq 1 20); do
      curl -sf -m 2 "http://127.0.0.1:$BACKEND_PORT/api/v1/health" >/dev/null 2>&1 && break
      sleep 1
    done
    curl -sf -m 2 "http://127.0.0.1:$BACKEND_PORT/api/v1/health" \
      >/dev/null 2>&1 && echo "backend up (pid $(cat "$PIDFILE_BACKEND"))" \
      || { echo "backend FAILED to start — see $BACKEND_LOG"; cat "$BACKEND_LOG"; return 1; }
  fi

  # ---- Frontend: Vite via node (npm .bin wrappers lack /usr/bin/env on Termux) ----
  if [ -f "$PIDFILE_FRONTEND" ] && kill -0 "$(cat "$PIDFILE_FRONTEND")" 2>/dev/null; then
    echo "frontend already running (pid $(cat "$PIDFILE_FRONTEND"))"
  else
    echo "starting frontend :${FRONTEND_PORT} ..."
    VITE_API_URL="http://127.0.0.1:$BACKEND_PORT" \
    VITE_WS_URL="ws://127.0.0.1:$BACKEND_PORT" \
      setsid nohup bash -c \
        "cd '$REPO/frontend' && exec node node_modules/vite/bin/vite.js" \
        --port "$FRONTEND_PORT" --host \
        --strictPort \
        > "$FRONTEND_LOG" 2>&1 < /dev/null &
    echo $! > "$PIDFILE_FRONTEND"
    for _ in $(seq 1 30); do
      curl -sf -m 2 "http://127.0.0.1:$FRONTEND_PORT/" >/dev/null 2>&1 && break
      sleep 1
    done
    curl -sf -m 2 "http://127.0.0.1:$FRONTEND_PORT/" \
      >/dev/null 2>&1 && echo "frontend up (pid $(cat "$PIDFILE_FRONTEND"))" \
      || { echo "frontend FAILED to start — see $FRONTEND_LOG"; cat "$FRONTEND_LOG"; return 1; }
  fi

  echo
  LAN_IP="$(hostname -I 2>/dev/null | awk '{print $1}' | tr -d ' ')"
  [ -z "$LAN_IP" ] && LAN_IP="$(python3 -c "
import socket
s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
try:
    s.connect(('8.8.8.8', 80)); print(s.getsockname()[0])
except Exception: pass
" 2>/dev/null)"
  echo "Git-Fix is live:"
  echo "  App:      http://127.0.0.1:$FRONTEND_PORT/  (network: http://${LAN_IP:-<lan-ip>}:$FRONTEND_PORT/)"
  echo "  Backend:  http://127.0.0.1:$BACKEND_PORT/api/v1/health"
  echo "  Logs:     $BACKEND_LOG  |  $FRONTEND_LOG"
}

cmd_stop() {
  for pair in "FRONTEND:$PIDFILE_FRONTEND" "BACKEND:$PIDFILE_BACKEND"; do
    name="${pair%%:*}"; pf="${pair##*:}"
    if [ -f "$pf" ]; then
      pid="$(cat "$pf")"
      # kill process group (setsid means the pid is its group leader)
      kill -- "-$pid" 2>/dev/null || kill "$pid" 2>/dev/null || true
      rm -f "$pf"
      echo "$name stopped (pid $pid)"
    fi
  done
  pkill -f "node_modules/vite/bin/vite.js" 2>/dev/null || true
  pkill -f "python3 -m backend.app" 2>/dev/null || true
}

cmd_status() {
  for pair in "BACKEND:$PIDFILE_BACKEND;http://127.0.0.1:$BACKEND_PORT/api/v1/health" \
              "FRONTEND:$PIDFILE_FRONTEND;http://127.0.0.1:$FRONTEND_PORT/"; do
    name="${pair%%:*}"; rest="${pair#*:}"
    pf="${rest%%;*}"; url="${rest#*;}"; url="${url%%;*}"
    if [ -f "$pf" ] && kill -0 "$(cat "$pf")" 2>/dev/null; then
      code="$(curl -s -o /dev/null -w '%{http_code}' -m 3 "$url" 2>/dev/null || echo dead)"
      echo "$name: RUNNING (pid $(cat "$pf"), http $code)"
    else
      echo "$name: stopped"
    fi
  done
}

case "${1:-status}" in
  start) cmd_start ;;
  stop)  cmd_stop; echo "done" ;;
  status) cmd_status ;;
  restart) cmd_stop; cmd_start ;;
  *) echo "usage: $0 {start|stop|status|restart}"; exit 1 ;;
esac