"""
Tests — DRAPE Backend
Run with: pytest tests/ -v
"""

import pytest
import io
from unittest.mock import patch, MagicMock


# ── Prompt Engine Tests ───────────────────────────────────────────────────────

def test_prompt_always_contains_outfit_lock():
    """Every prompt must include the garment-lock instruction block."""
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from services.prompt_engine import build_prompt, OUTFIT_LOCK_BLOCK
    from models.schemas import ReferenceMeta, ReferenceType

    result = build_prompt(outfit_filename="test-dress.jpg", references=[])
    assert "OUTFIT LOCK" in result["prompt"]
    assert "MANDATORY PRESERVATION" in result["prompt"]


def test_negative_prompt_covers_all_garment_attributes():
    """Negative prompt must prohibit changes to all key garment elements."""
    from services.prompt_engine import build_prompt

    result = build_prompt(outfit_filename="test-blazer.jpg", references=[])
    neg = result["negative_prompt"].lower()

    required_attrs = [
        "color", "pattern", "collar", "sleeve", "hemline",
        "buttons", "stitching", "seams", "fabric",
    ]
    for attr in required_attrs:
        assert attr in neg, f"Negative prompt missing attribute: '{attr}'"


def test_custom_notes_go_into_creative_block_not_outfit_lock():
    """User custom notes must NOT appear inside the outfit lock block."""
    from services.prompt_engine import build_prompt, OUTFIT_LOCK_BLOCK

    custom = "Use a dark moody vibe with dramatic lighting."
    result = build_prompt(outfit_filename="jeans.jpg", references=[], custom_notes=custom)

    prompt = result["prompt"]
    lock_end = prompt.index("CREATIVE DIRECTION")
    # The custom note should appear AFTER the creative direction header
    assert custom in prompt
    assert prompt.index(custom) > lock_end


def test_batch_prompts_preserve_outfit_lock_per_outfit():
    """Batch prompt builder should produce one entry per outfit with locks."""
    from services.prompt_engine import build_batch_prompts

    outfits = [
        {"outfit_id": "id1", "filename": "dress.jpg"},
        {"outfit_id": "id2", "filename": "jacket.jpg"},
    ]
    results = build_batch_prompts(outfits, references=[])
    assert len(results) == 2
    for r in results:
        assert "OUTFIT LOCK" in r["prompt"]
        assert r["outfit_id"] in ("id1", "id2")


def test_prompt_output_block_present():
    """Output spec block must be in every prompt."""
    from services.prompt_engine import build_prompt

    result = build_prompt("shirt.jpg", references=[])
    assert "commercial fashion photography" in result["prompt"].lower()
    assert "photorealistic" in result["prompt"].lower()


# ── Storage Tests ─────────────────────────────────────────────────────────────

def test_save_and_retrieve_outfit():
    """Saved outfit should be retrievable by ID."""
    from services import storage

    fake_bytes = b"\xff\xd8\xff\xe0" + b"\x00" * 100  # minimal JPEG header
    meta = storage.save_outfit(
        file_bytes=fake_bytes,
        original_filename="test-outfit.jpg",
        sku="SKU-001",
    )
    assert meta.outfit_id
    assert meta.sku == "SKU-001"

    retrieved = storage.get_outfit(meta.outfit_id)
    assert retrieved is not None
    assert retrieved.filename == "test-outfit.jpg"


def test_save_and_retrieve_reference():
    """Saved reference should be retrievable by ID."""
    from services import storage
    from models.schemas import ReferenceType

    fake_bytes = b"\xff\xd8\xff\xe0" + b"\x00" * 100
    meta = storage.save_reference(
        file_bytes=fake_bytes,
        original_filename="vibe-ref.jpg",
        ref_type=ReferenceType.VIBE,
    )
    assert meta.ref_id
    assert meta.ref_type == ReferenceType.VIBE

    retrieved = storage.get_reference(meta.ref_id)
    assert retrieved is not None


def test_job_lifecycle():
    """Job should transition through pending → processing states."""
    from services import storage

    job_id = storage.create_job(["outfit-1", "outfit-2"], images_per_outfit=3)
    job = storage.get_job(job_id)
    assert job["status"] == "pending"
    assert job["total_requested"] == 6

    storage.update_job(job_id, status="processing", completed=2)
    job = storage.get_job(job_id)
    assert job["status"] == "processing"
    assert job["completed"] == 2


# ── ZIP Handler Tests ─────────────────────────────────────────────────────────

def test_zip_validation_rejects_non_zip():
    """Non-ZIP bytes should fail validation."""
    from utils.zip_handler import validate_zip

    result = validate_zip(b"this is not a zip file")
    assert result["valid"] is False
    assert result["image_count"] == 0


def test_zip_extraction_filters_hidden_files():
    """ZIP extractor should skip __MACOSX and dotfiles."""
    import zipfile, io
    from utils.zip_handler import extract_images

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("outfit.jpg", b"\xff\xd8\xff\xe0" + b"\x00" * 50)
        zf.writestr("__MACOSX/._outfit.jpg", b"garbage")
        zf.writestr(".hidden.jpg", b"\xff\xd8\xff\xe0" + b"\x00" * 50)

    result = extract_images(buf.getvalue())
    filenames = [r["filename"] for r in result]
    assert "outfit.jpg" in filenames
    assert "._outfit.jpg" not in filenames
    assert ".hidden.jpg" not in filenames


# ── Image Validation Tests ────────────────────────────────────────────────────

def test_image_validation_rejects_oversized():
    """Files larger than MAX_FILE_SIZE_MB should be rejected."""
    from utils.image_utils import validate_image_bytes

    big_bytes = b"\xff\xd8\xff\xe0" + b"\x00" * (51 * 1024 * 1024)  # 51 MB
    valid, err = validate_image_bytes(big_bytes, "big.jpg")
    assert not valid
    assert "limit" in err.lower()


def test_image_validation_rejects_wrong_extension():
    """Unsupported file extensions should be rejected."""
    from utils.image_utils import validate_image_bytes

    valid, err = validate_image_bytes(b"\x00" * 100, "file.bmp")
    assert not valid
    assert "bmp" in err.lower() or "unsupported" in err.lower()


def test_image_validation_accepts_valid_jpg():
    """Valid JPEG bytes with .jpg extension should pass."""
    from utils.image_utils import validate_image_bytes

    jpeg_bytes = b"\xff\xd8\xff\xe0" + b"\x00" * 1000
    valid, err = validate_image_bytes(jpeg_bytes, "outfit.jpg")
    assert valid
    assert err == ""


# ── API Endpoint Tests (requires running app) ─────────────────────────────────

@pytest.fixture
def client():
    """FastAPI test client."""
    from fastapi.testclient import TestClient
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from main import app
    return TestClient(app)


def test_health_endpoint(client):
    """Health check should return 200 with model info."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "nano-banana-2" in data["model"]


def test_upload_outfit_invalid_file(client):
    """Uploading a non-image should return 400."""
    response = client.post(
        "/api/upload/outfit",
        files={"files": ("test.txt", b"hello world", "text/plain")},
    )
    assert response.status_code == 400


def test_list_outfits_returns_array(client):
    """GET /api/upload/outfits should return a list."""
    response = client.get("/api/upload/outfits")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_gallery_empty_initially(client):
    """Gallery should return empty groups with no jobs run."""
    response = client.get("/api/gallery/")
    assert response.status_code == 200
    data = response.json()
    assert "groups" in data
    assert isinstance(data["groups"], list)


def test_admin_stats_structure(client):
    """Admin stats should return expected fields."""
    response = client.get("/api/admin/stats")
    assert response.status_code == 200
    data = response.json()
    for field in [
        "total_outfits_uploaded", "total_references_uploaded",
        "total_images_generated", "total_failed", "active_jobs",
    ]:
        assert field in data, f"Missing field: {field}"
