"""
Gallery Router
==============
Returns generated images grouped by outfit for the frontend gallery view.
"""

from fastapi import APIRouter, HTTPException
from models.schemas import GalleryResponse, GalleryGroup
from services import storage
from config import settings

router = APIRouter()


@router.get("/", response_model=GalleryResponse)
async def get_gallery():
    """Return all generated images grouped by outfit."""
    all_generated = storage.get_all_generated()
    groups = []
    total_images = 0

    for outfit_id, images in all_generated.items():
        outfit = storage.get_outfit(outfit_id)
        if not outfit:
            continue

        successful_images = [img for img in images if img.status == "success"]
        total_images += len(successful_images)

        # Outfit thumbnail URL
        import os
        from pathlib import Path
        outfit_path = Path(outfit.upload_path)
        outfit_url = f"/uploads/outfits/{outfit_id}/{outfit_path.name}"

        group = GalleryGroup(
            outfit_id=outfit_id,
            outfit_filename=outfit.filename,
            outfit_url=outfit_url,
            sku=outfit.sku,
            name=outfit.name,
            images=images,          # include failed too so UI can show errors
            generated_at=outfit.uploaded_at,
        )
        groups.append(group)

    return GalleryResponse(
        total_outfits=len(groups),
        total_images=total_images,
        groups=groups,
    )


@router.get("/outfit/{outfit_id}")
async def get_outfit_gallery(outfit_id: str):
    """Return generated images for a single outfit."""
    outfit = storage.get_outfit(outfit_id)
    if not outfit:
        raise HTTPException(status_code=404, detail=f"Outfit {outfit_id} not found.")

    images = storage.get_generated_images(outfit_id)
    return {
        "outfit_id": outfit_id,
        "outfit_filename": outfit.filename,
        "images": images,
    }
