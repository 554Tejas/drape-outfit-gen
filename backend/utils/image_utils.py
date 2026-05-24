"""
Image Utilities
===============
Validation, resizing, and format conversion helpers for uploaded images.
"""

import io
import logging
from pathlib import Path
from typing import Tuple

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_FILE_SIZE_MB = 50


def validate_image_bytes(data: bytes, filename: str) -> Tuple[bool, str]:
    """
    Validate that the provided bytes are a supported image.

    Returns (is_valid, error_message)
    """
    size_mb = len(data) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        return False, f"File exceeds {MAX_FILE_SIZE_MB} MB limit ({size_mb:.1f} MB)"

    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"Unsupported file type '{ext}'. Allowed: {ALLOWED_EXTENSIONS}"

    # Minimal header check
    magic = {
        b"\xff\xd8\xff": "jpeg",
        b"\x89PNG":       "png",
        b"RIFF":          "webp",
    }
    for header, fmt in magic.items():
        if data[:len(header)] == header:
            return True, ""

    # Soft pass if extension is valid — let PIL catch real corruption
    return True, ""


def normalize_image(data: bytes, max_dim: int = 2048) -> bytes:
    """
    Resize image so neither dimension exceeds max_dim,
    and convert to JPEG for uniform storage.

    Requires Pillow.
    """
    try:
        from PIL import Image

        img = Image.open(io.BytesIO(data))
        img = img.convert("RGB")

        w, h = img.size
        if max(w, h) > max_dim:
            scale = max_dim / max(w, h)
            img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

        out = io.BytesIO()
        img.save(out, format="JPEG", quality=92)
        return out.getvalue()
    except ImportError:
        logger.warning("Pillow not installed — skipping image normalization")
        return data
    except Exception as exc:
        logger.error("Image normalization failed: %s", exc)
        return data


def get_image_dimensions(data: bytes) -> Tuple[int, int]:
    """Return (width, height) of image bytes. Returns (0, 0) on failure."""
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(data))
        return img.size
    except Exception:
        return 0, 0
