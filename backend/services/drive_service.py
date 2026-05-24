"""
Google Drive Ingestion Service
================================
Reads image files from a shared Google Drive folder.
Requires a service account with read access to the target folder,
or the folder must be set to "Anyone with the link can view".

Dependencies: google-api-python-client, google-auth
"""

import io
import logging
import re
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# ── Drive folder ID extractor ─────────────────────────────────────────────────

def extract_folder_id(folder_url: str) -> str:
    """
    Extract Google Drive folder ID from a share URL.

    Supports:
    - https://drive.google.com/drive/folders/{id}
    - https://drive.google.com/drive/u/0/folders/{id}
    - Raw folder ID strings
    """
    patterns = [
        r"drive\.google\.com/drive(?:/u/\d+)?/folders/([a-zA-Z0-9_-]+)",
        r"^([a-zA-Z0-9_-]{25,})$",
    ]
    for pattern in patterns:
        m = re.search(pattern, folder_url)
        if m:
            return m.group(1)
    raise ValueError(f"Cannot extract folder ID from URL: {folder_url}")


# ── Drive client factory ──────────────────────────────────────────────────────

def _build_drive_service():
    """Build an authenticated Google Drive API service client."""
    try:
        import google.auth
        import google.auth.transport.requests
        from googleapiclient.discovery import build

        creds, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/drive.readonly"]
        )
        return build("drive", "v3", credentials=creds, cache_discovery=False)
    except ImportError:
        raise RuntimeError(
            "google-api-python-client not installed. "
            "Run: pip install google-api-python-client google-auth"
        )
    except Exception as exc:
        raise RuntimeError(f"Failed to build Drive service: {exc}") from exc


# ── Image file listing ────────────────────────────────────────────────────────

IMAGE_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
}


def list_images_in_folder(folder_id: str) -> List[Dict]:
    """
    List all image files in a Google Drive folder.

    Returns list of { id, name, mimeType }
    """
    service = _build_drive_service()
    mime_filter = " or ".join(f"mimeType='{m}'" for m in IMAGE_MIME_TYPES)
    query = f"'{folder_id}' in parents and ({mime_filter}) and trashed=false"

    results = (
        service.files()
        .list(q=query, fields="files(id, name, mimeType)", pageSize=200)
        .execute()
    )
    files = results.get("files", [])
    logger.info("Found %d image(s) in Drive folder %s", len(files), folder_id)
    return files


# ── File download ─────────────────────────────────────────────────────────────

def download_file(file_id: str) -> bytes:
    """Download a Google Drive file by ID and return raw bytes."""
    try:
        from googleapiclient.http import MediaIoBaseDownload

        service = _build_drive_service()
        request = service.files().get_media(fileId=file_id)
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        return buffer.getvalue()
    except Exception as exc:
        raise RuntimeError(f"Failed to download Drive file {file_id}: {exc}") from exc


# ── High-level ingest ─────────────────────────────────────────────────────────

def ingest_folder(folder_url: str) -> List[Dict]:
    """
    Download all images from a Google Drive folder.

    Returns list of { filename, bytes }
    """
    folder_id = extract_folder_id(folder_url)
    files = list_images_in_folder(folder_id)
    ingested = []
    for f in files:
        try:
            data = download_file(f["id"])
            ingested.append({"filename": f["name"], "bytes": data})
            logger.info("Downloaded %s from Drive", f["name"])
        except Exception as exc:
            logger.error("Failed to download %s: %s", f["name"], exc)
    return ingested
