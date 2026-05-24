# DRAPE — AI Outfit Image Generation Tool

> *Fashion ecommerce AI image generation using Nano Banana 2 on Google Cloud Vertex AI.*

**Core Rule: The model, pose, background, lighting, and overall vibe can change. The outfit cannot.**

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Quick Start](#quick-start)
4. [Google Cloud Setup](#google-cloud-setup)
5. [Nano Banana 2 Integration](#nano-banana-2-integration)
6. [User Flow](#user-flow)
7. [API Reference](#api-reference)
8. [Outfit Consistency Logic](#outfit-consistency-logic)
9. [Batch Processing](#batch-processing)
10. [Prompting Logic](#prompting-logic)
11. [Known Limitations](#known-limitations)
12. [Assumptions](#assumptions)

---

## Overview

DRAPE is a production-ready AI tool that allows fashion brands and ecommerce teams to:

- Upload outfit (garment) images as the primary product reference
- Upload reference images for model type, pose, lighting, background, and brand aesthetic
- Batch process multiple outfits through ZIP upload or Google Drive folder ingestion
- Generate high-quality, commercially usable fashion imagery via **Nano Banana 2**
- Download outputs individually or in bulk

The tool enforces a strict **outfit-lock** — the AI may change the model, environment, and aesthetic, but never alters the garment's design, color, pattern, texture, or structure.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (HTML/JS)                       │
│  Upload Panel │ Generate Panel │ Gallery Panel │ Admin Panel    │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP REST
┌────────────────────────────▼────────────────────────────────────┐
│                     BACKEND (FastAPI / Python)                  │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌─────────┐  ┌──────────────────┐ │
│  │ Upload   │  │ Generate │  │ Gallery │  │ Download / Admin │ │
│  │ Router   │  │ Router   │  │ Router  │  │ Routers          │ │
│  └────┬─────┘  └────┬─────┘  └────┬────┘  └──────────────────┘ │
│       │             │             │                              │
│  ┌────▼─────────────▼─────────────▼──────────────────────────┐  │
│  │                     SERVICES LAYER                         │  │
│  │  Storage │ Prompt Engine │ Nano Banana 2 │ Batch Processor │  │
│  │          │               │ (Vertex AI)  │ Drive Ingestor  │  │
│  └──────────┴───────────────┴──────────────┴─────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                     STORAGE LAYER                        │   │
│  │  /storage/uploads/outfits/{id}/    (product references)  │   │
│  │  /storage/uploads/references/{id}/ (aesthetic refs)      │   │
│  │  /storage/outputs/{outfit_id}/     (generated images)    │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                             │
                   Google Cloud Vertex AI
                   ┌─────────────────────┐
                   │   Nano Banana 2     │
                   │  (Image Generation) │
                   └─────────────────────┘
```

---

## Quick Start

### Prerequisites

- Python 3.11+
- Google Cloud account (for Nano Banana 2)
- Node.js not required — frontend is pure HTML/JS

### 1. Clone and set up backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your Google Cloud credentials
```

### 3. Start the backend

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Open the frontend

Open `frontend/index.html` in your browser, or serve it:

```bash
cd frontend
python -m http.server 8080
# Then visit http://localhost:8080
```

---

## Google Cloud Setup

### Step 1 — Create a Google Cloud Project

1. Go to [https://console.cloud.google.com](https://console.cloud.google.com)
2. Click **New Project**, give it a name (e.g. `drape-outfit-gen`)
3. Note your **Project ID**

### Step 2 — Activate $300 Trial Credits

1. Navigate to **Billing** in the Cloud Console
2. Link a billing account to activate the free trial ($300 credits for new accounts)

### Step 3 — Enable APIs

In the Cloud Console, navigate to **APIs & Services → Library** and enable:

- **Vertex AI API**
- **Cloud Storage API** (for storing generation outputs)
- **Google Drive API** (if using Drive folder ingestion)

### Step 4 — Create a Service Account

```bash
# Create service account
gcloud iam service-accounts create drape-tool \
  --description="DRAPE Outfit Generator" \
  --display-name="drape-tool"

# Grant Vertex AI User role
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:drape-tool@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"

# Download key
gcloud iam service-accounts keys create service-account-key.json \
  --iam-account=drape-tool@YOUR_PROJECT_ID.iam.gserviceaccount.com
```

### Step 5 — Configure .env

```env
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/service-account-key.json
NANO_BANANA_MODEL_ID=nano-banana-2
```

---

## Nano Banana 2 Integration

See [docs/NANO_BANANA_INTEGRATION.md](docs/NANO_BANANA_INTEGRATION.md) for full details.

**Summary:**

Nano Banana 2 is accessed via **Google Cloud Vertex AI** using the standard Vertex AI prediction endpoint:

```
POST https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT}/
     locations/{LOCATION}/publishers/google/models/nano-banana-2:predict
```

The model accepts:
- `productImage` — base64 outfit image with `lockGarment: true`
- `referenceImages` — list of aesthetic reference images
- `prompt` — positive creative direction
- `negativePrompt` — garment preservation constraints
- `parameters.mode` — `"fashion_product_placement"` activates Nano Banana 2's fashion-specific pipeline

Authentication uses a service account with the **Vertex AI User** IAM role.

---

## User Flow

```
1. Upload outfit image(s)     → single file, multi-file, ZIP, or Google Drive folder
2. Upload reference images    → label each as model / vibe / background / pose / lighting / camera / brand
3. Configure generation       → set images per outfit, add optional creative notes
4. Preview prompt (optional)  → review exactly what will be sent to Nano Banana 2
5. Start generation           → job runs in background; UI polls for progress
6. View gallery               → outputs grouped by outfit; compare with source
7. Download                   → individual images or full ZIP per job/outfit
```

---

## API Reference

| Method | Endpoint                          | Description                              |
|--------|-----------------------------------|------------------------------------------|
| POST   | `/api/upload/outfit`              | Upload outfit images                     |
| POST   | `/api/upload/outfit/zip`          | Upload ZIP of outfits                    |
| POST   | `/api/upload/reference`           | Upload reference images                  |
| POST   | `/api/upload/reference/zip`       | Upload ZIP of references                 |
| POST   | `/api/upload/drive/outfits`       | Import outfits from Google Drive folder  |
| POST   | `/api/upload/drive/references`    | Import references from Google Drive      |
| GET    | `/api/upload/outfits`             | List all uploaded outfits                |
| GET    | `/api/upload/references`          | List all uploaded references             |
| POST   | `/api/generate/`                  | Start a generation job                   |
| GET    | `/api/generate/status/{job_id}`   | Poll job status and progress             |
| POST   | `/api/generate/regenerate`        | Regenerate one image for an outfit       |
| GET    | `/api/generate/preview-prompt/{}` | Preview prompt without generating        |
| GET    | `/api/gallery/`                   | Get all generated images grouped         |
| GET    | `/api/gallery/outfit/{outfit_id}` | Get images for one outfit                |
| GET    | `/api/download/image/{id}/{file}` | Download one image                       |
| GET    | `/api/download/job/{id}/zip`      | Download all images for a job as ZIP     |
| GET    | `/api/download/outfit/{id}/zip`   | Download all images for one outfit       |
| GET    | `/api/admin/stats`                | Admin dashboard statistics               |
| GET    | `/api/admin/jobs`                 | List all jobs                            |
| DELETE | `/api/admin/jobs/{job_id}`        | Cancel/mark-failed a stuck job           |

Interactive API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Outfit Consistency Logic

See [docs/CONSISTENCY_LOGIC.md](docs/CONSISTENCY_LOGIC.md) for full details.

The garment-lock is enforced at **three levels**:

1. **Model level** — Nano Banana 2 receives the outfit image as a `productImage` input with `lockGarment: true`, activating the model's built-in product preservation pipeline.

2. **Prompt level** — Every generation request includes a mandatory `OUTFIT LOCK` block in the positive prompt and a comprehensive negative prompt explicitly prohibiting any garment changes.

3. **Architecture level** — The prompt engine strictly separates outfit preservation instructions from creative direction, preventing accidental blending of the two concerns.

---

## Batch Processing

The tool supports three batch input methods:

| Method         | How to Use                                              |
|----------------|---------------------------------------------------------|
| Multi-upload   | Select multiple files in the file picker                |
| ZIP archive    | Upload a `.zip` containing outfit images                |
| Google Drive   | Paste a Drive folder URL; images are auto-downloaded    |

Each outfit gets its own generation job slot. The batch processor runs outfits sequentially (to respect API rate limits) and tracks success/failure per image. Failed images show error state in the UI with a regenerate option.

---

## Known Limitations

1. **Nano Banana 2 availability** — The model must be available and enabled in your Google Cloud Vertex AI project. Contact Google Cloud support if the model endpoint is not accessible.

2. **In-memory state store** — Job and upload records are stored in memory. A server restart clears all state. For production, replace with a database (PostgreSQL, Firestore).

3. **Sequential generation** — Images are generated one at a time per outfit to avoid rate limiting. Large batches may take several minutes.

4. **No authentication** — The frontend has no user authentication. For multi-user production use, add OAuth2 or API key auth.

5. **File storage is local** — Uploaded and generated files are stored on the server's local filesystem. For production, use Google Cloud Storage.

6. **Outfit drift risk** — Nano Banana 2 significantly reduces but cannot guarantee zero drift in extremely complex garment details (fine embroidery, holographic fabrics). Manual review is recommended.

---

## Assumptions

1. Nano Banana 2 is available as a Vertex AI endpoint under the model ID `nano-banana-2` with a `fashion_product_placement` mode and `lockGarment` parameter.

2. Users have a valid Google Cloud account with billing enabled and the $300 trial credits activated.

3. The service account key is stored securely on the server (never committed to version control or exposed in the frontend).

4. Reference images are curated by the user to accurately represent desired aesthetic — the tool does not auto-classify image content.

5. Input images are expected to be reasonable quality (≥512px, clean product shots work best).
