"""
AI Outfit Image Generation Tool — Backend
FastAPI application entry point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import uvicorn
import os

from routers import upload, generate, gallery, download, admin
from config import settings

app = FastAPI(
    title="AI Outfit Image Generation Tool",
    description="Fashion ecommerce AI image generation using Nano Banana 2",
    version="1.0.0",
)

# ── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static file serving ───────────────────────────────────────────────────────
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.OUTPUT_DIR, exist_ok=True)

app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")
app.mount("/outputs", StaticFiles(directory=settings.OUTPUT_DIR), name="outputs")

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(upload.router,   prefix="/api/upload",   tags=["Upload"])
app.include_router(generate.router, prefix="/api/generate", tags=["Generate"])
app.include_router(gallery.router,  prefix="/api/gallery",  tags=["Gallery"])
app.include_router(download.router, prefix="/api/download", tags=["Download"])
app.include_router(admin.router,    prefix="/api/admin",    tags=["Admin"])


@app.get("/health")
async def health_check():
    return {"status": "ok", "model": "nano-banana-2", "platform": "google-cloud-vertex-ai"}


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"error": str(exc), "message": "Internal server error"},
    )


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
