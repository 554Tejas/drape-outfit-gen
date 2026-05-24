#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# DRAPE — Setup Script
# Usage: bash scripts/setup.sh
# Installs backend deps, creates .env from example, and verifies Google auth.
# ──────────────────────────────────────────────────────────────────────────────

set -e
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"

echo -e "${CYAN}"
echo "  ██████╗ ██████╗  █████╗ ██████╗ ███████╗"
echo "  ██╔══██╗██╔══██╗██╔══██╗██╔══██╗██╔════╝"
echo "  ██║  ██║██████╔╝███████║██████╔╝█████╗  "
echo "  ██║  ██║██╔══██╗██╔══██║██╔═══╝ ██╔══╝  "
echo "  ██████╔╝██║  ██║██║  ██║██║     ███████╗"
echo "  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚══════╝"
echo -e "${NC}"
echo "  AI Outfit Image Generation Tool — Setup"
echo ""

# ── Python version check ──────────────────────────────────────────────────────
echo -e "${CYAN}[1/5] Checking Python version...${NC}"
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

if [[ "$PYTHON_MAJOR" -lt 3 ]] || [[ "$PYTHON_MAJOR" -eq 3 && "$PYTHON_MINOR" -lt 11 ]]; then
  echo -e "${RED}✗ Python 3.11+ required. Found: $PYTHON_VERSION${NC}"
  exit 1
fi
echo -e "${GREEN}✓ Python $PYTHON_VERSION${NC}"

# ── Virtual environment ───────────────────────────────────────────────────────
echo -e "${CYAN}[2/5] Creating virtual environment...${NC}"
cd "$BACKEND_DIR"
if [[ ! -d "venv" ]]; then
  python3 -m venv venv
  echo -e "${GREEN}✓ venv created${NC}"
else
  echo -e "${YELLOW}  venv already exists — skipping${NC}"
fi

# Activate
source venv/bin/activate 2>/dev/null || { echo -e "${RED}Failed to activate venv${NC}"; exit 1; }

# ── Install dependencies ──────────────────────────────────────────────────────
echo -e "${CYAN}[3/5] Installing Python dependencies...${NC}"
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
echo -e "${GREEN}✓ Dependencies installed${NC}"

# ── Create .env ───────────────────────────────────────────────────────────────
echo -e "${CYAN}[4/5] Configuring environment...${NC}"
if [[ ! -f ".env" ]]; then
  cp .env.example .env
  echo -e "${YELLOW}  Created .env from .env.example${NC}"
  echo -e "${YELLOW}  ➜ Edit backend/.env and fill in your Google Cloud credentials${NC}"
else
  echo -e "${YELLOW}  .env already exists — skipping${NC}"
fi

# Create storage directories
mkdir -p storage/uploads/outfits storage/uploads/references storage/outputs storage/temp
echo -e "${GREEN}✓ Storage directories ready${NC}"

# ── Verify Google auth ────────────────────────────────────────────────────────
echo -e "${CYAN}[5/5] Verifying Google Cloud authentication...${NC}"
python3 -c "
import os, sys
creds_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', '')
if not creds_path or not os.path.exists(creds_path):
    print('  GOOGLE_APPLICATION_CREDENTIALS not set or file not found.')
    print('  Set it in backend/.env before running the server.')
    sys.exit(0)
try:
    import google.auth, google.auth.transport.requests
    creds, project = google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
    creds.refresh(google.auth.transport.requests.Request())
    print(f'  Auth OK — project: {project}')
except Exception as e:
    print(f'  Auth check failed: {e}')
    print('  Verify your service account key and GOOGLE_APPLICATION_CREDENTIALS path.')
" 2>/dev/null || true

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  Setup complete!${NC}"
echo ""
echo "  Next steps:"
echo "  1. Edit backend/.env with your Google Cloud credentials"
echo "  2. Run the backend:"
echo "       cd backend && source venv/bin/activate"
echo "       uvicorn main:app --host 0.0.0.0 --port 8000 --reload"
echo ""
echo "  3. Open the frontend:"
echo "       cd frontend && python3 -m http.server 8080"
echo "       Visit http://localhost:8080"
echo ""
echo "  API docs: http://localhost:8000/docs"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
