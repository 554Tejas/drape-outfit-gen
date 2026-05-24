#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# DRAPE — Dev Start Script
# Usage: bash scripts/start.sh
# Starts backend (port 8000) and frontend (port 8080) in parallel.
# Press Ctrl+C to stop both.
# ──────────────────────────────────────────────────────────────────────────────

set -e
CYAN='\033[0;36m'
GREEN='\033[0;32m'
NC='\033[0m'

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Cleanup on Ctrl+C
cleanup() {
  echo -e "\n${CYAN}Stopping servers...${NC}"
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
  exit 0
}
trap cleanup SIGINT SIGTERM

# ── Backend ───────────────────────────────────────────────────────────────────
echo -e "${CYAN}Starting backend on http://localhost:8000 ...${NC}"
cd "$ROOT_DIR/backend"
source venv/bin/activate 2>/dev/null || { echo "Run scripts/setup.sh first."; exit 1; }
uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Wait for backend to be ready
sleep 2

# ── Frontend ──────────────────────────────────────────────────────────────────
echo -e "${CYAN}Starting frontend on http://localhost:8080 ...${NC}"
cd "$ROOT_DIR/frontend"
python3 -m http.server 8080 &
FRONTEND_PID=$!

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  DRAPE is running!${NC}"
echo ""
echo "  Frontend : http://localhost:8080"
echo "  Backend  : http://localhost:8000"
echo "  API Docs : http://localhost:8000/docs"
echo ""
echo "  Press Ctrl+C to stop."
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Keep alive
wait
