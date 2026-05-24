"""
Upload Router
=============
Handles:
 - Single / multi outfit image upload
 - Single / multi reference image upload
 - ZIP archive upload (outfits and/or references)
 - Google Drive folder ingestion
"""

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from typing import List, Optional

from models.schemas import OutfitMeta, ReferenceMeta, ReferenceType, DriveIngestRequest
from services import storage, drive_service
from utils.zip_handler import extract_images, validate_zip
from utils.image_utils import validate_image_bytes

router = APIRouter()


# ── Outfit uploads ────────────────────────────────────────────────────────────

@router.post("/outfit", response_model=List[OutfitMeta])
async def upload_outfits(
    files: List[UploadFile] = File(...),
    sku: Optional[str]        = Form(None),
    name: Optional[str]       = Form(None),
    collection: Optional[str] = Form(None),
    category: Optional[str]   = Form(None),
):
    """Upload one or more outfit images."""
    saved = []
    for file in files:
        data = await file.read()
        valid, err = validate_image_bytes(data, file.filename)
        if not valid:
            raise HTTPException(status_code=400, detail=f"{file.filename}: {err}")

        meta = storage.save_outfit(
            file_bytes=data,
            original_filename=file.filename,
            sku=sku,
            name=name,
            collection=collection,
            category=category,
        )
        saved.append(meta)

    return saved


@router.post("/outfit/zip", response_model=List[OutfitMeta])
async def upload_outfit_zip(
    file: UploadFile = File(...),
    collection: Optional[str] = Form(None),
    category: Optional[str]   = Form(None),
):
    """Upload a ZIP archive containing multiple outfit images."""
    if not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only .zip files are accepted here.")

    data = await file.read()
    validation = validate_zip(data)
    if not validation["valid"]:
        raise HTTPException(status_code=400, detail=str(validation["errors"]))
    if validation["image_count"] == 0:
        raise HTTPException(status_code=400, detail="No image files found in ZIP archive.")

    images = extract_images(data)
    saved = []
    for img in images:
        valid, err = validate_image_bytes(img["bytes"], img["filename"])
        if not valid:
            continue
        meta = storage.save_outfit(
            file_bytes=img["bytes"],
            original_filename=img["filename"],
            collection=collection,
            category=category,
        )
        saved.append(meta)

    return saved


# ── Reference uploads ─────────────────────────────────────────────────────────

@router.post("/reference", response_model=List[ReferenceMeta])
async def upload_references(
    files: List[UploadFile] = File(...),
    ref_type: ReferenceType  = Form(ReferenceType.OTHER),
):
    """Upload one or more reference images (vibe, model, pose, lighting, etc.)."""
    saved = []
    for file in files:
        data = await file.read()
        valid, err = validate_image_bytes(data, file.filename)
        if not valid:
            raise HTTPException(status_code=400, detail=f"{file.filename}: {err}")

        meta = storage.save_reference(
            file_bytes=data,
            original_filename=file.filename,
            ref_type=ref_type,
        )
        saved.append(meta)

    return saved


@router.post("/reference/zip", response_model=List[ReferenceMeta])
async def upload_reference_zip(
    file: UploadFile  = File(...),
    ref_type: ReferenceType = Form(ReferenceType.OTHER),
):
    """Upload a ZIP archive of reference images."""
    if not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only .zip files accepted.")

    data = await file.read()
    validation = validate_zip(data)
    if not validation["valid"]:
        raise HTTPException(status_code=400, detail=str(validation["errors"]))

    images = extract_images(data)
    saved = []
    for img in images:
        valid, err = validate_image_bytes(img["bytes"], img["filename"])
        if not valid:
            continue
        meta = storage.save_reference(
            file_bytes=img["bytes"],
            original_filename=img["filename"],
            ref_type=ref_type,
        )
        saved.append(meta)

    return saved


# ── Google Drive ingestion ────────────────────────────────────────────────────

@router.post("/drive/outfits", response_model=List[OutfitMeta])
async def ingest_drive_outfits(body: DriveIngestRequest):
    """Ingest outfit images from a Google Drive folder URL."""
    try:
        images = drive_service.ingest_folder(body.folder_url)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    saved = []
    for img in images:
        meta = storage.save_outfit(
            file_bytes=img["bytes"],
            original_filename=img["filename"],
        )
        saved.append(meta)

    return saved


@router.post("/drive/references", response_model=List[ReferenceMeta])
async def ingest_drive_references(body: DriveIngestRequest):
    """Ingest reference images from a Google Drive folder URL."""
    try:
        images = drive_service.ingest_folder(body.folder_url)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    ref_type = body.ref_type or ReferenceType.OTHER
    saved = []
    for img in images:
        meta = storage.save_reference(
            file_bytes=img["bytes"],
            original_filename=img["filename"],
            ref_type=ref_type,
        )
        saved.append(meta)

    return saved


# ── List endpoints ────────────────────────────────────────────────────────────

@router.get("/outfits", response_model=List[OutfitMeta])
async def list_outfits():
    return storage.list_outfits()


@router.get("/references", response_model=List[ReferenceMeta])
async def list_references():
    return storage.list_references()
