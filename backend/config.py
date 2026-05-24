"""
Configuration and environment settings
"""

from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    # ── App ──────────────────────────────────────────────────────────────────
    APP_NAME: str = "AI Outfit Image Generation Tool"
    DEBUG: bool = False
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080", "http://127.0.0.1:8080", "http://127.0.0.1:8000", "http://localhost:8000", "*"]

    # ── Storage ───────────────────────────────────────────────────────────────
    BASE_DIR: str = os.path.dirname(os.path.abspath(__file__))
    UPLOAD_DIR: str = os.path.join(BASE_DIR, "storage", "uploads")
    OUTPUT_DIR: str = os.path.join(BASE_DIR, "storage", "outputs")
    TEMP_DIR: str = os.path.join(BASE_DIR, "storage", "temp")
    MAX_UPLOAD_SIZE_MB: int = 50  # per file

    # ── Google Cloud / Nano Banana 2 ──────────────────────────────────────────
    GOOGLE_CLOUD_PROJECT: str = ""
    GOOGLE_CLOUD_LOCATION: str = "us-central1"
    GOOGLE_APPLICATION_CREDENTIALS: str = ""   # path to service-account JSON
    NANO_BANANA_MODEL_ID: str = "nano-banana-2"
    NANO_BANANA_ENDPOINT: str = ""             # Vertex AI endpoint URL (override)
    GENERATION_TIMEOUT_SEC: int = 120

    # ── Google Drive ──────────────────────────────────────────────────────────
    GOOGLE_DRIVE_ENABLED: bool = True
    GOOGLE_DRIVE_SCOPES: List[str] = [
        "https://www.googleapis.com/auth/drive.readonly"
    ]

    # ── Generation defaults ───────────────────────────────────────────────────
    DEFAULT_IMAGES_PER_OUTFIT: int = 4
    MAX_IMAGES_PER_OUTFIT: int = 10
    OUTPUT_IMAGE_FORMAT: str = "PNG"
    OUTPUT_IMAGE_WIDTH: int = 1024
    OUTPUT_IMAGE_HEIGHT: int = 1365   # 3:4 fashion ratio

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

# Ensure storage directories exist on import
for d in [settings.UPLOAD_DIR, settings.OUTPUT_DIR, settings.TEMP_DIR]:
    os.makedirs(d, exist_ok=True)
