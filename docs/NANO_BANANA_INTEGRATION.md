# Nano Banana 2 — Integration Guide

## What Is Nano Banana 2?

Nano Banana 2 is a fashion-specialized image generation model hosted on **Google Cloud Vertex AI**. It is purpose-built for fashion ecommerce and campaign imagery, with native support for:

- **Product image conditioning** — takes an existing garment photo as a locked reference
- **Multi-reference aesthetic guidance** — accepts multiple vibe/model/background reference images
- **Fashion product placement mode** — places the locked outfit onto a generated scene without redesigning it
- **Negative prompting** — explicit instruction tokens to prevent garment alteration

---

## Endpoint

```
POST https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/
     locations/{LOCATION}/publishers/google/models/nano-banana-2:predict
```

**Default location:** `us-central1`

---

## Authentication

Authentication uses a **Google service account** with the `roles/aiplatform.user` IAM role.

The backend uses `google-auth` to fetch short-lived OAuth2 tokens automatically:

```python
import google.auth
import google.auth.transport.requests

creds, _ = google.auth.default(
    scopes=["https://www.googleapis.com/auth/cloud-platform"]
)
creds.refresh(google.auth.transport.requests.Request())
token = creds.token
```

The `GOOGLE_APPLICATION_CREDENTIALS` environment variable must point to your service account JSON key file.

---

## Request Payload

```json
{
  "instances": [
    {
      "productImage": {
        "bytesBase64Encoded": "<base64-encoded outfit image>",
        "mimeType": "image/jpeg",
        "lockGarment": true
      },
      "referenceImages": [
        { "bytesBase64Encoded": "<base64 vibe ref>", "mimeType": "image/jpeg" },
        { "bytesBase64Encoded": "<base64 model ref>", "mimeType": "image/jpeg" }
      ],
      "prompt": "OUTFIT LOCK — MANDATORY PRESERVATION: ...\nCREATIVE DIRECTION: ...",
      "negativePrompt": "Do NOT change: outfit design, color, pattern..."
    }
  ],
  "parameters": {
    "sampleCount": 1,
    "aspectRatio": "1024:1365",
    "outputMimeType": "image/png",
    "safetyFilterLevel": "block_few",
    "personGeneration": "allow_all",
    "mode": "fashion_product_placement"
  }
}
```

### Key Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| `lockGarment` | `true` | Activates Nano Banana 2's garment preservation pipeline |
| `mode` | `fashion_product_placement` | Fashion-specific generation pipeline |
| `sampleCount` | `1` | Images per API call (we call once per image to handle failures gracefully) |
| `aspectRatio` | `1024:1365` | 3:4 portrait — standard fashion ecommerce ratio |
| `personGeneration` | `allow_all` | Required to generate model-wearing-outfit scenes |

---

## Response Format

```json
{
  "predictions": [
    {
      "bytesBase64Encoded": "<base64-encoded generated PNG>",
      "mimeType": "image/png"
    }
  ]
}
```

The backend decodes the base64 bytes and saves them to `/storage/outputs/{outfit_id}/`.

---

## Error Handling

| HTTP Status | Meaning | Action |
|-------------|---------|--------|
| `200` | Success | Decode and save image |
| `400` | Bad request (invalid payload) | Log and mark image as failed |
| `401` | Auth error | Refresh token / check service account |
| `429` | Rate limit | Retry with exponential backoff |
| `500` | Model server error | Retry once; mark failed if persistent |

---

## Cost Estimation

Nano Banana 2 pricing on Vertex AI (approximate, check current pricing in Cloud Console):

- ~$0.04–0.08 per generated image
- 4 images × 10 outfits = 40 images ≈ $1.60–$3.20 per batch
- $300 trial credits support approximately **4,000–7,500 images**

---

## Enabling the Model in Google Cloud

1. Go to **Vertex AI → Model Garden** in the Cloud Console
2. Search for **Nano Banana 2**
3. Click **Enable** / **Deploy**
4. Note the endpoint URL or use the auto-built endpoint (recommended)

---

## Local Testing Without Google Cloud

To test the full UI flow without a live Nano Banana 2 connection, set `NANO_BANANA_MODEL_ID=mock` in your `.env`. The backend will use a mock generation service that returns placeholder images, allowing you to validate the entire workflow (upload → prompt → batch → gallery → download) locally.

```env
# .env (for local testing only)
NANO_BANANA_MODEL_ID=mock
GOOGLE_CLOUD_PROJECT=   # leave empty for mock mode
```
