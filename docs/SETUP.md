# DRAPE — Setup Guide

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.11+ | [python.org](https://python.org) |
| pip | Latest | Comes with Python |
| Google Cloud SDK | Latest | [cloud.google.com/sdk](https://cloud.google.com/sdk) |
| A modern browser | — | Chrome / Firefox / Edge |

---

## Step 1 — Google Cloud Project Setup

### 1.1 Create a Project

1. Go to [https://console.cloud.google.com](https://console.cloud.google.com)
2. Click **Select a project → New Project**
3. Name it (e.g. `drape-outfit-gen`) and note your **Project ID**

### 1.2 Activate $300 Free Trial Credits

1. In the Cloud Console, go to **Billing**
2. Click **Activate free trial** — requires a credit card for verification (not charged during trial)
3. The $300 credit activates automatically for new eligible accounts

### 1.3 Enable Required APIs

In the Cloud Console go to **APIs & Services → Library** and enable:

- ✅ **Vertex AI API**
- ✅ **Cloud Storage API**
- ✅ **Google Drive API** *(only if using Drive folder ingestion)*
- ✅ **IAM Service Account Credentials API**

Or enable all at once via CLI:

```bash
gcloud services enable \
  aiplatform.googleapis.com \
  storage.googleapis.com \
  drive.googleapis.com \
  --project=YOUR_PROJECT_ID
```

### 1.4 Create a Service Account

```bash
# Create the service account
gcloud iam service-accounts create drape-tool \
  --description="DRAPE AI Outfit Generator" \
  --display-name="drape-tool" \
  --project=YOUR_PROJECT_ID

# Grant Vertex AI User role (for Nano Banana 2 access)
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:drape-tool@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"

# Grant Storage Object Admin (for output storage if using GCS)
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:drape-tool@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"

# Download the service account key JSON
gcloud iam service-accounts keys create \
  ./backend/service-account-key.json \
  --iam-account=drape-tool@YOUR_PROJECT_ID.iam.gserviceaccount.com
```

> ⚠️ **SECURITY**: `service-account-key.json` is listed in `.gitignore`.
> Never commit it to version control or expose it in the frontend.

---

## Step 2 — Backend Setup

### 2.1 Create Virtual Environment

```bash
cd outfit-gen-tool/backend
python -m venv venv

# Activate (macOS/Linux)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate
```

### 2.2 Install Dependencies

```bash
pip install -r requirements.txt
```

### 2.3 Configure Environment Variables

```bash
cp .env.example .env
```

Open `.env` and fill in your values:

```env
# ── Google Cloud ──────────────────────────────────────────────────
GOOGLE_CLOUD_PROJECT=your-project-id-here
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/backend/service-account-key.json

# ── Nano Banana 2 ─────────────────────────────────────────────────
NANO_BANANA_MODEL_ID=nano-banana-2

# ── Optional overrides ────────────────────────────────────────────
# NANO_BANANA_ENDPOINT=https://custom-endpoint-if-provided-by-google
# DEBUG=true
```

### 2.4 Verify Google Auth

```bash
python -c "
import google.auth, google.auth.transport.requests
creds, project = google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
creds.refresh(google.auth.transport.requests.Request())
print(f'Auth OK — project: {project}, token: {creds.token[:20]}...')
"
```

### 2.5 Start the Backend

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Backend is now running at: **http://localhost:8000**

Interactive API docs: **http://localhost:8000/docs**

---

## Step 3 — Frontend Setup

The frontend requires no build step — it's a single HTML file.

### Option A: Open directly in browser (simplest)

```bash
open frontend/index.html          # macOS
xdg-open frontend/index.html      # Linux
start frontend/index.html         # Windows
```

### Option B: Serve via Python HTTP server (recommended)

```bash
cd frontend
python -m http.server 8080
# Visit http://localhost:8080
```

### Option C: Serve via the backend (production-like)

The backend already mounts `/uploads` and `/outputs` as static paths.
To also serve the frontend HTML, add to `backend/main.py`:

```python
from fastapi.responses import FileResponse

@app.get("/")
async def serve_frontend():
    return FileResponse("../frontend/index.html")
```

---

## Step 4 — Docker (Optional)

### Build and run with Docker Compose

```bash
# From the project root
docker-compose up --build
```

Services:
- Backend: **http://localhost:8000**
- Frontend: **http://localhost:8080**

### Stop

```bash
docker-compose down
```

---

## Step 5 — Verify the Full Flow

1. Open the frontend at `http://localhost:8080`
2. In the **Upload** tab, upload a test outfit image (JPG/PNG)
3. Upload a reference image (set type to `vibe`)
4. Switch to the **Generate** tab
5. Select the outfit and reference, set count to 1
6. Click **Preview Prompt** — verify the outfit lock block is present
7. Click **Generate** — watch the job progress bar
8. Switch to the **Gallery** tab — generated image should appear
9. Click **↓ Save** to download the image

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `GOOGLE_APPLICATION_CREDENTIALS` not found | Use absolute path in `.env`; confirm file exists |
| `DefaultCredentialsError` | Run `gcloud auth application-default login` as fallback |
| Nano Banana 2 returns 404 | Confirm the model ID and location in your Vertex AI console |
| Nano Banana 2 returns 403 | Service account missing `roles/aiplatform.user` |
| CORS error in browser | Ensure backend is on port 8000 and `ALLOWED_ORIGINS` includes your frontend URL |
| ZIP upload fails | ZIP may be corrupted or contain no valid image files |
| Drive ingestion fails | Share folder as "Anyone with link" or grant service account access |
| Images not showing in gallery | Check that `/outputs` static mount is working; verify image paths |
