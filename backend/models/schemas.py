"""
Pydantic schemas — request / response models
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
import datetime


class ReferenceType(str, Enum):
    MODEL       = "model"
    BACKGROUND  = "background"
    POSE        = "pose"
    LIGHTING    = "lighting"
    VIBE        = "vibe"
    CAMERA      = "camera"
    BRAND       = "brand"
    OTHER       = "other"


class JobStatus(str, Enum):
    PENDING     = "pending"
    PROCESSING  = "processing"
    COMPLETED   = "completed"
    FAILED      = "failed"
    PARTIAL     = "partial"


# ── Upload ────────────────────────────────────────────────────────────────────

class OutfitMeta(BaseModel):
    outfit_id: str
    filename: str
    sku: Optional[str] = None
    name: Optional[str] = None
    collection: Optional[str] = None
    category: Optional[str] = None
    upload_path: str
    uploaded_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)


class ReferenceMeta(BaseModel):
    ref_id: str
    filename: str
    ref_type: ReferenceType = ReferenceType.OTHER
    upload_path: str
    uploaded_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)


class DriveIngestRequest(BaseModel):
    folder_url: str
    ref_type: Optional[ReferenceType] = None


# ── Generation ────────────────────────────────────────────────────────────────

class GenerationRequest(BaseModel):
    outfit_ids: List[str]              = Field(..., description="IDs of uploaded outfit images")
    reference_ids: List[str]           = Field(default=[], description="IDs of uploaded reference images")
    images_per_outfit: int             = Field(default=4, ge=1, le=10)
    custom_prompt_notes: Optional[str] = Field(None, description="Optional extra creative direction")
    preview_prompts: bool              = Field(False, description="Return prompts without generating")


class GeneratedImage(BaseModel):
    image_id: str
    outfit_id: str
    filename: str
    url: str
    prompt_used: str
    generation_index: int
    consistency_flags: List[str] = []
    status: str = "success"
    error: Optional[str] = None


class JobResult(BaseModel):
    job_id: str
    status: JobStatus
    outfit_ids: List[str]
    total_requested: int
    completed: int
    failed: int
    images: List[GeneratedImage] = []
    started_at: Optional[datetime.datetime] = None
    completed_at: Optional[datetime.datetime] = None
    error_log: List[str] = []


class PromptPreviewResponse(BaseModel):
    outfit_id: str
    outfit_filename: str
    prompt: str
    negative_prompt: str


# ── Gallery ───────────────────────────────────────────────────────────────────

class GalleryGroup(BaseModel):
    outfit_id: str
    outfit_filename: str
    outfit_url: str
    sku: Optional[str] = None
    name: Optional[str] = None
    images: List[GeneratedImage]
    generated_at: Optional[datetime.datetime] = None


class GalleryResponse(BaseModel):
    total_outfits: int
    total_images: int
    groups: List[GalleryGroup]


# ── Admin ─────────────────────────────────────────────────────────────────────

class AdminStats(BaseModel):
    total_outfits_uploaded: int
    total_references_uploaded: int
    total_images_generated: int
    total_failed: int
    active_jobs: int
    storage_used_mb: float
    recent_jobs: List[Dict[str, Any]] = []
