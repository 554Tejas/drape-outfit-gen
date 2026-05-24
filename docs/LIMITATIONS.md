# Known Limitations & Possible Improvements

## Known Limitations

### 1. Nano Banana 2 Availability
**Current state:** Nano Banana 2 must be available and enabled on your Google Cloud
Vertex AI project. If the model ID `nano-banana-2` is not yet accessible in your
project region, contact Google Cloud support or check the Vertex AI Model Garden
for the exact model name and endpoint.

**Impact:** Without a working model endpoint, image generation will return 404 or 403.
All other features (upload, prompt preview, gallery, download) function independently.

---

### 2. In-Memory State Store
**Current state:** All job records, outfit metadata, and reference metadata are stored
in Python dictionaries in process memory. A server restart clears all state.

**Impact:** Uploaded file records are lost on restart (the physical files remain on
disk but cannot be referenced). Long-running servers are fine; dev restarts require
re-uploading.

---

### 3. Sequential Image Generation
**Current state:** Images are generated one at a time per outfit, and outfits are
processed one at a time. This avoids API rate limits but is slow for large batches.

**Impact:** 10 outfits × 4 images each = 40 sequential API calls. At ~15s per call
(typical for Vertex AI image generation), this is ~10 minutes for the full batch.

---

### 4. No User Authentication
**Current state:** The frontend and API have no authentication layer. Any user with
access to the URL can upload, generate, and download.

**Impact:** Not suitable for multi-tenant or public-facing production use.

---

### 5. Local File Storage
**Current state:** All uploaded and generated files are stored on the server's local
filesystem under `backend/storage/`.

**Impact:** Files are not replicated, not backed up, and not accessible across multiple
server instances. Disk fills up without cleanup jobs.

---

### 6. Outfit Drift on Complex Garments
**Current state:** The three-layer consistency enforcement (model flag + prompt lock +
architectural separation) significantly reduces but cannot guarantee zero drift.

**Impact:** Fine embroidery, holographic fabrics, and small-print patterns may be
approximated rather than reproduced exactly. Manual review is always recommended.

---

### 7. No Real-Time WebSocket Updates
**Current state:** Job progress is polled every 2.5 seconds via HTTP GET.

**Impact:** Slightly laggy UI updates; minor extra server load. Not a functional issue.

---

### 8. No Consistency Scoring
**Current state:** The UI shows a manual review checklist approach; no automated
outfit-drift scoring is implemented.

**Impact:** Reviewers must manually compare outputs to source garments.

---

## Possible Improvements

### Short-Term (1–2 weeks)

| Improvement | Description | Effort |
|-------------|-------------|--------|
| **PostgreSQL / Firestore** | Replace in-memory store with a proper database | Medium |
| **WebSocket progress** | Replace polling with `WebSocket` for real-time job updates | Low |
| **Auto-SKU tagging** | Parse filename patterns to auto-extract SKU codes | Low |
| **Thumbnail generation** | Generate 256px thumbnails for faster gallery loading | Low |
| **Cleanup job** | Scheduled task to delete temp files older than N days | Low |
| **Rate limit handling** | Retry with exponential backoff on 429 from Vertex AI | Low |

---

### Medium-Term (1–4 weeks)

| Improvement | Description | Effort |
|-------------|-------------|--------|
| **Google Cloud Storage** | Store uploads and outputs in GCS instead of local disk | Medium |
| **Parallel batch processing** | Generate multiple outfits concurrently with a semaphore | Medium |
| **Consistency scorer** | Use a vision model (e.g. Gemini) to compare outfit vs output and score drift | High |
| **User authentication** | Add Google OAuth2 login via Firebase Auth | Medium |
| **Editable prompt layer** | Full prompt editor in the UI with live preview | Medium |
| **Before/after comparison** | Side-by-side slider in gallery: source outfit vs generated image | Low |
| **Output naming by SKU** | Name generated files with SKU and collection for easy asset management | Low |

---

### Long-Term (Production-Ready)

| Improvement | Description | Effort |
|-------------|-------------|--------|
| **Cloud Run / GKE deployment** | Deploy backend as a containerized Cloud Run service | High |
| **Celery + Redis job queue** | Replace FastAPI BackgroundTasks with a durable job queue | High |
| **Multi-tenant support** | Separate storage and job namespaces per user / brand | High |
| **Campaign mode** | Pre-define a full shoot brief (10+ references, model specs, brand guide) and apply to 100+ SKUs | High |
| **Revision tracking** | Track multiple generations per outfit with version history | Medium |
| **API key management** | Allow brands to generate API keys for direct integration with their PIM/DAM | Medium |
| **Batch export to GCS bucket** | Direct export of a shoot batch to a structured GCS folder / Drive | Medium |

---

## Assumptions Made During Build

1. **Nano Banana 2 model ID**: Assumed to be `nano-banana-2` in Vertex AI, with a
   `fashion_product_placement` mode and `lockGarment` parameter. The exact API
   contract must be confirmed with Google Cloud documentation once the model is
   available in your project.

2. **Authentication via ADC**: Assumed that Application Default Credentials (ADC)
   are the correct auth mechanism. Service account key path is set via
   `GOOGLE_APPLICATION_CREDENTIALS`.

3. **Image format**: Output images are generated as PNG at 1024×1365 (3:4 ratio),
   suitable for ecommerce product cards and campaign portraits.

4. **Reference classification**: Users are expected to manually classify reference
   images (model, pose, background, etc.). Automatic classification by a vision model
   was excluded from the MVP scope.

5. **Single user**: The tool is designed for a single user or small team with direct
   access. Multi-tenancy and access control are out of scope for this submission.

6. **Outfit images are product shots**: Input outfits are expected to be flat-lay,
   ghost mannequin, or simple model shots — not editorial collages or lookbook
   composites.
