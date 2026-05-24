# DRAPE — System Architecture

## Overview

DRAPE follows a clean three-tier architecture:

```
Browser (HTML/JS)
      │
      │  REST API (JSON)
      ▼
FastAPI Backend (Python)
      │
      │  Vertex AI REST (HTTPS)
      ▼
Nano Banana 2 (Google Cloud)
```

---

## Layer Breakdown

### 1. Frontend — `frontend/index.html`

A single-file, dependency-free HTML/CSS/JS application.

**Panels:**
| Panel | Purpose |
|-------|---------|
| Upload | Outfit images + reference images (single, multi, ZIP, Drive) |
| Generate | Select outfits + refs, configure count, preview prompt, start job |
| Gallery | View generated images grouped by outfit, download individual or bulk |
| Admin | Live stats dashboard, job log, cancel stuck jobs |

**API communication:** Native `fetch()`, polling every 2.5s for job status.

---

### 2. Backend — `backend/`

Built with **FastAPI** (Python 3.11+). Async throughout.

```
backend/
├── main.py                   Entry point, CORS, static mounts
├── config.py                 All settings, reads from .env
├── requirements.txt
│
├── models/
│   └── schemas.py            Pydantic models for all request/response types
│
├── routers/
│   ├── upload.py             POST /api/upload/* (outfit, reference, ZIP, Drive)
│   ├── generate.py           POST /api/generate/, GET status, regenerate, preview
│   ├── gallery.py            GET /api/gallery/
│   ├── download.py           GET /api/download/* (image, ZIP)
│   └── admin.py              GET /api/admin/stats, jobs; DELETE jobs/{id}
│
├── services/
│   ├── storage.py            In-memory state + local file I/O
│   ├── prompt_engine.py      Structured prompt construction
│   ├── nano_banana.py        Vertex AI / Nano Banana 2 API client
│   ├── batch_processor.py    Async job orchestrator (runs as background task)
│   └── drive_service.py      Google Drive folder ingestion
│
└── utils/
    ├── zip_handler.py        ZIP extraction + validation
    └── image_utils.py        Image validation, resizing, format conversion
```

---

### 3. Storage Layout

```
backend/storage/
├── uploads/
│   ├── outfits/
│   │   └── {outfit_id}/
│   │       └── outfit.jpg        (the locked product reference)
│   └── references/
│       └── {ref_id}/
│           └── ref.jpg           (vibe / model / pose / lighting refs)
│
└── outputs/
    └── {outfit_id}/
        ├── gen_01_a1b2c3d4.png
        ├── gen_02_e5f6g7h8.png
        └── job_{job_id}.zip      (created on bulk download)
```

---

### 4. Nano Banana 2 — Generation Layer

See `docs/NANO_BANANA_INTEGRATION.md` for full API details.

**Request flow:**

```
batch_processor.run_batch_job()
    │
    ├── For each outfit_id:
    │       prompt_engine.build_prompt()  →  { prompt, negative_prompt }
    │       nano_banana.generate_batch()  →  List[bytes | None]
    │           │
    │           └── For each image (count):
    │                   nano_banana.generate_image()
    │                       │
    │                       ├── _get_access_token()  (google-auth ADC)
    │                       ├── _build_endpoint()    (Vertex AI URL)
    │                       ├── _encode_image()      (base64)
    │                       └── httpx.AsyncClient.post()  → image bytes
    │
    └── storage.save_generated_image() / record_failed_image()
```

---

### 5. Prompt Engine — Two-Block Design

The prompt engine **always** separates:

```
┌────────────────────────────────────────────────┐
│ BLOCK A — OUTFIT LOCK (constant)               │
│ Describes the garment in absolute terms.       │
│ Applied to EVERY request.                      │
│ Cannot be modified by user custom notes.       │
└────────────────────────────────────────────────┘

┌────────────────────────────────────────────────┐
│ BLOCK B — CREATIVE DIRECTION (variable)        │
│ Interprets reference image types (model, pose, │
│ background, lighting, vibe, camera, brand).    │
│ User custom notes are appended here only.      │
└────────────────────────────────────────────────┘

┌────────────────────────────────────────────────┐
│ BLOCK C — NEGATIVE PROMPT (constant)           │
│ Explicitly prohibits garment changes.          │
│ Applied to EVERY request.                      │
└────────────────────────────────────────────────┘

┌────────────────────────────────────────────────┐
│ BLOCK D — OUTPUT SPEC (constant)               │
│ Defines format, realism, aspect ratio,         │
│ commercial usability goal.                     │
└────────────────────────────────────────────────┘
```

---

### 6. Job Lifecycle

```
POST /api/generate/
        │
        ├── Validate outfit IDs exist
        ├── storage.create_job()        → job_id, status=pending
        ├── background_tasks.add_task() → batch_processor.run_batch_job()
        └── Return { job_id, status=pending } immediately

Background (async):
        ├── status → processing
        ├── For each outfit:
        │       generate images → save or record_failed
        │       update job (completed++, failed++)
        └── status → completed | partial | failed

Frontend polls GET /api/generate/status/{job_id} every 2.5s
        └── When terminal status → load gallery
```

---

### 7. Scalability Path

| Component | Current | Production Upgrade |
|-----------|---------|-------------------|
| State store | In-memory dict | PostgreSQL / Firestore |
| File storage | Local filesystem | Google Cloud Storage |
| Job queue | FastAPI BackgroundTasks | Cloud Tasks / Celery + Redis |
| Auth | None | OAuth2 / API keys |
| Concurrency | Sequential per outfit | Parallel with rate limiting |
| Deployment | `uvicorn` direct | Cloud Run / GKE |
