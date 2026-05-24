"""
Download Router
===============
Allows users to download individual images or full job output as ZIP.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path

from services import storage
from config import settings

router = APIRouter()


@router.get("/image/{outfit_id}/{filename}")
async def download_image(outfit_id: str, filename: str):
    """Download a single generated image."""
    path = Path(settings.OUTPUT_DIR) / outfit_id / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Image not found.")
    return FileResponse(path, media_type="image/png", filename=filename)


@router.get("/job/{job_id}/zip")
async def download_job_zip(job_id: str):
    """Download all generated images for a job as a ZIP archive."""
    job = storage.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found.")
    if job["status"] not in ("completed", "partial"):
        raise HTTPException(
            status_code=400,
            detail=f"Job is not yet complete (status: {job['status']}).",
        )

    zip_path = storage.create_zip_for_job(job_id)
    if not zip_path or not Path(zip_path).exists():
        raise HTTPException(status_code=500, detail="Failed to create ZIP archive.")

    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename=f"generated_outfits_{job_id[:8]}.zip",
    )


@router.get("/outfit/{outfit_id}/zip")
async def download_outfit_zip(outfit_id: str):
    """Download all generated images for a single outfit as ZIP."""
    outfit = storage.get_outfit(outfit_id)
    if not outfit:
        raise HTTPException(status_code=404, detail=f"Outfit {outfit_id} not found.")

    import zipfile, io
    from fastapi.responses import StreamingResponse

    images = storage.get_generated_images(outfit_id)
    successful = [img for img in images if img.status == "success"]

    if not successful:
        raise HTTPException(status_code=404, detail="No successful images for this outfit.")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for img in successful:
            img_path = Path(settings.OUTPUT_DIR) / outfit_id / img.filename
            if img_path.exists():
                zf.write(img_path, img.filename)
    buf.seek(0)

    safe_name = outfit.filename.replace(" ", "_").replace("/", "_")
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}_outputs.zip"'},
    )
