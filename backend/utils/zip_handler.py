"""
ZIP Handler Utility
===================
Extracts outfit images and reference images from uploaded ZIP archives.
Automatically detects image files and maps them to the correct storage buckets.
"""

import io
import logging
import zipfile
from pathlib import Path
from typing import List, Dict

logger = logging.getLogger(__name__)

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def is_image(filename: str) -> bool:
    return Path(filename).suffix.lower() in IMAGE_EXTENSIONS


def _is_hidden(name: str) -> bool:
    """Skip macOS __MACOSX and hidden dot-files."""
    parts = Path(name).parts
    return any(p.startswith(".") or p == "__MACOSX" for p in parts)


def extract_images(zip_bytes: bytes) -> List[Dict]:
    """
    Extract all image files from a ZIP archive.

    Returns
    -------
    List of { filename: str, bytes: bytes }
    """
    results = []
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        for name in zf.namelist():
            if _is_hidden(name):
                continue
            if not is_image(name):
                continue
            with zf.open(name) as fh:
                data = fh.read()
            # Use only the base filename, not the full path inside the zip
            results.append({
                "filename": Path(name).name,
                "bytes": data,
            })
            logger.info("Extracted image from ZIP: %s (%d bytes)", name, len(data))

    logger.info("Total images extracted from ZIP: %d", len(results))
    return results


def validate_zip(zip_bytes: bytes) -> Dict:
    """
    Validate a ZIP without fully extracting it.

    Returns { valid: bool, image_count: int, errors: list }
    """
    errors = []
    image_count = 0
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            bad = zf.testzip()
            if bad:
                errors.append(f"Corrupt file in ZIP: {bad}")
            for name in zf.namelist():
                if not _is_hidden(name) and is_image(name):
                    image_count += 1
    except zipfile.BadZipFile as exc:
        errors.append(f"Invalid ZIP file: {exc}")

    return {
        "valid": len(errors) == 0,
        "image_count": image_count,
        "errors": errors,
    }
