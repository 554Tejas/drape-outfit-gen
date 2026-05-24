"""
Storage Service
===============
Manages local file system storage for uploads, outputs, and temp files.
Provides a clean interface used by all other services.
"""

import os
import shutil
import uuid
import json
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
import datetime

from config import settings
from models.schemas import OutfitMeta, ReferenceMeta, ReferenceType, GeneratedImage

logger = logging.getLogger(__name__)

# ── State store (in-memory, replace with DB in production) ────────────────────

_outfits: Dict[str, OutfitMeta] = {}
_references: Dict[str, ReferenceMeta] = {}
_jobs: Dict[str, Dict[str, Any]] = {}
_generated: Dict[str, List[GeneratedImage]] = {}  # outfit_id -> images


# ── Outfit storage ────────────────────────────────────────────────────────────

def save_outfit(
    file_bytes: bytes,
    original_filename: str,
    sku: Optional[str] = None,
    name: Optional[str] = None,
    collection: Optional[str] = None,
    category: Optional[str] = None,
) -> OutfitMeta:
    outfit_id = str(uuid.uuid4())
    ext = Path(original_filename).suffix.lower() or ".jpg"
    dest_dir = Path(settings.UPLOAD_DIR) / "outfits" / outfit_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / f"outfit{ext}"

    with open(dest_path, "wb") as fh:
        fh.write(file_bytes)

    meta = OutfitMeta(
        outfit_id=outfit_id,
        filename=original_filename,
        sku=sku,
        name=name,
        collection=collection,
        category=category,
        upload_path=str(dest_path),
    )
    _outfits[outfit_id] = meta
    logger.info("Saved outfit %s -> %s", outfit_id, dest_path)
    return meta


def get_outfit(outfit_id: str) -> Optional[OutfitMeta]:
    return _outfits.get(outfit_id)


def list_outfits() -> List[OutfitMeta]:
    return list(_outfits.values())


# ── Reference storage ─────────────────────────────────────────────────────────

def save_reference(
    file_bytes: bytes,
    original_filename: str,
    ref_type: ReferenceType = ReferenceType.OTHER,
) -> ReferenceMeta:
    ref_id = str(uuid.uuid4())
    ext = Path(original_filename).suffix.lower() or ".jpg"
    dest_dir = Path(settings.UPLOAD_DIR) / "references" / ref_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / f"ref{ext}"

    with open(dest_path, "wb") as fh:
        fh.write(file_bytes)

    meta = ReferenceMeta(
        ref_id=ref_id,
        filename=original_filename,
        ref_type=ref_type,
        upload_path=str(dest_path),
    )
    _references[ref_id] = meta
    logger.info("Saved reference %s (%s) -> %s", ref_id, ref_type.value, dest_path)
    return meta


def get_reference(ref_id: str) -> Optional[ReferenceMeta]:
    return _references.get(ref_id)


def get_references_by_ids(ref_ids: List[str]) -> List[ReferenceMeta]:
    return [_references[r] for r in ref_ids if r in _references]


def list_references() -> List[ReferenceMeta]:
    return list(_references.values())


# ── Output storage ────────────────────────────────────────────────────────────

def save_generated_image(
    image_bytes: bytes,
    outfit_id: str,
    generation_index: int,
    prompt_used: str,
) -> GeneratedImage:
    image_id = str(uuid.uuid4())
    dest_dir = Path(settings.OUTPUT_DIR) / outfit_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    filename = f"gen_{generation_index + 1:02d}_{image_id[:8]}.png"
    dest_path = dest_dir / filename

    with open(dest_path, "wb") as fh:
        fh.write(image_bytes)

    rel_url = f"/outputs/{outfit_id}/{filename}"
    img = GeneratedImage(
        image_id=image_id,
        outfit_id=outfit_id,
        filename=filename,
        url=rel_url,
        prompt_used=prompt_used,
        generation_index=generation_index,
        status="success",
    )

    _generated.setdefault(outfit_id, []).append(img)
    logger.info("Saved generated image %s for outfit %s", filename, outfit_id)
    return img


def record_failed_image(outfit_id: str, generation_index: int, error: str) -> GeneratedImage:
    img = GeneratedImage(
        image_id=str(uuid.uuid4()),
        outfit_id=outfit_id,
        filename="",
        url="",
        prompt_used="",
        generation_index=generation_index,
        status="failed",
        error=error,
    )
    _generated.setdefault(outfit_id, []).append(img)
    return img


def get_generated_images(outfit_id: str) -> List[GeneratedImage]:
    return _generated.get(outfit_id, [])


def get_all_generated() -> Dict[str, List[GeneratedImage]]:
    return dict(_generated)


# ── Job tracking ──────────────────────────────────────────────────────────────

def create_job(outfit_ids: List[str], images_per_outfit: int) -> str:
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "outfit_ids": outfit_ids,
        "total_requested": len(outfit_ids) * images_per_outfit,
        "completed": 0,
        "failed": 0,
        "images": [],
        "started_at": datetime.datetime.utcnow().isoformat(),
        "completed_at": None,
        "error_log": [],
    }
    return job_id


def update_job(job_id: str, **kwargs):
    if job_id in _jobs:
        _jobs[job_id].update(kwargs)


def get_job(job_id: str) -> Optional[Dict]:
    return _jobs.get(job_id)


def list_jobs() -> List[Dict]:
    return list(_jobs.values())


# ── Zip creation ──────────────────────────────────────────────────────────────

def create_zip_for_job(job_id: str) -> Optional[str]:
    """Zip all generated outputs for a job."""
    import zipfile

    job = _jobs.get(job_id)
    if not job:
        return None

    zip_path = Path(settings.OUTPUT_DIR) / f"job_{job_id}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for outfit_id in job["outfit_ids"]:
            for img in _generated.get(outfit_id, []):
                if img.status == "success":
                    full_path = Path(settings.OUTPUT_DIR) / outfit_id / img.filename
                    if full_path.exists():
                        arcname = f"{outfit_id}/{img.filename}"
                        zf.write(full_path, arcname)

    return str(zip_path)


# ── Storage stats ─────────────────────────────────────────────────────────────

def storage_stats() -> Dict[str, Any]:
    def dir_size_mb(path: str) -> float:
        total = 0
        for f in Path(path).rglob("*"):
            if f.is_file():
                total += f.stat().st_size
        return round(total / (1024 * 1024), 2)

    generated_count = sum(
        1 for imgs in _generated.values()
        for img in imgs if img.status == "success"
    )
    failed_count = sum(
        1 for imgs in _generated.values()
        for img in imgs if img.status == "failed"
    )

    return {
        "total_outfits_uploaded":    len(_outfits),
        "total_references_uploaded": len(_references),
        "total_images_generated":    generated_count,
        "total_failed":              failed_count,
        "active_jobs":               sum(1 for j in _jobs.values() if j["status"] == "processing"),
        "storage_used_mb":           dir_size_mb(settings.UPLOAD_DIR) + dir_size_mb(settings.OUTPUT_DIR),
        "recent_jobs":               list(reversed(list(_jobs.values())))[:10],
    }
