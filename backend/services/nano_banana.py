"""
Imagen 4 Generation + Gemini Vision — Google Cloud Vertex AI
"""

import base64
import logging
import asyncio
from pathlib import Path
from typing import List, Optional, Tuple

import httpx
from config import settings

logger = logging.getLogger(__name__)


def _get_access_token() -> str:
    try:
        import google.auth
        import google.auth.transport.requests
        creds, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        creds.refresh(google.auth.transport.requests.Request())
        return creds.token
    except Exception as exc:
        raise RuntimeError(f"Google Cloud authentication failed: {exc}") from exc


def _build_gemini_endpoint() -> str:
    project  = settings.GOOGLE_CLOUD_PROJECT
    location = settings.GOOGLE_CLOUD_LOCATION
    return (
        f"https://{location}-aiplatform.googleapis.com/v1/projects/{project}"
        f"/locations/{location}/publishers/google/models/gemini-2.5-flash-image:generateContent"
    )


def _encode_image(path: str) -> Tuple[str, str]:
    path = Path(path)
    mime_map = {
        ".jpg":  "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png":  "image/png",
        ".webp": "image/webp",
    }
    mime = mime_map.get(path.suffix.lower(), "image/jpeg")
    with open(path, "rb") as fh:
        return base64.b64encode(fh.read()).decode("utf-8"), mime


async def describe_outfit(outfit_image_path: str) -> str:
    """
    Use Gemini Vision to generate an accurate visual noun-phrase for the outfit.
    Includes logic to prevent 'pattern bleed' on the lower half.
    """
    try:
        endpoint = _build_gemini_endpoint()
        token    = _get_access_token()
        b64, mime = _encode_image(outfit_image_path)

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "inline_data": {
                                "mime_type": mime,
                                "data": b64,
                            }
                        },
                        {
                            "text": (
                                "You are a fashion product expert. Describe this garment in precise detail "
                                "for an AI text-to-image system. START YOUR RESPONSE DIRECTLY with the "
                                "garment description (e.g. 'A men's jacket...'). DO NOT use conversational "
                                "filler. Include: exact color palette, fabric type, "
                                "pattern or print description, silhouette, fit, collar type, sleeve style and length, "
                                "closure type (zip or buttons), pockets, cuffs, hemline, any logos/badges, "
                                "and overall style. "
                                "CRITICAL: If the garment shown is ONLY a top (e.g., a shirt, sweater, or jacket), "
                                "you MUST end your description with the exact phrase: 'paired with plain, solid-colored neutral trousers'. "
                                "If it is a full-body outfit (like a dress or suit), do not add this phrase. "
                                "Be extremely specific and factual about the colors and patterns. "
                                "Format as a single continuous paragraph."
                            )
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 300,
            }
        }

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type":  "application/json",
        }

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(endpoint, json=payload, headers=headers)

        if response.status_code == 200:
            result      = response.json()
            description = result["candidates"][0]["content"]["parts"][0]["text"].strip()
            logger.info("Outfit Description: %s", description)
            return description
        return ""
    except Exception as exc:
        logger.warning("Outfit description error: %s", exc)
        return ""


async def describe_scene(reference_image_path: str) -> str:
    """
    Use Gemini Vision to extract the background/environment from a reference image.
    """
    try:
        endpoint = _build_gemini_endpoint()
        token    = _get_access_token()
        b64, mime = _encode_image(reference_image_path)

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "inline_data": {
                                "mime_type": mime,
                                "data": b64,
                            }
                        },
                        {
                            "text": (
                                "Describe the background, setting, interior design, or landscape "
                                "shown in this image. Focus entirely on the environment, location, lighting, "
                                "and aesthetic details. IGNORE any people, clothing, or mannequins in the foreground. "
                                "Be highly descriptive but concise. Format as a single descriptive sentence."
                            )
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 150,
            }
        }

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type":  "application/json",
        }

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(endpoint, json=payload, headers=headers)

        if response.status_code == 200:
            result = response.json()
            description = result["candidates"][0]["content"]["parts"][0]["text"].strip()
            logger.info("Scene Description: %s", description)
            return description
        return ""
    except Exception as exc:
        logger.warning("Scene description error: %s", exc)
        return ""


async def generate_image(
    outfit_image_path: str,
    reference_image_paths: List[str],
    prompt: str,
    negative_prompt: str,
    width: int  = settings.OUTPUT_IMAGE_WIDTH,
    height: int = settings.OUTPUT_IMAGE_HEIGHT,
) -> bytes:

    # 1. Visually parse the outfit
    outfit_description = await describe_outfit(outfit_image_path)

    # 2. Visually parse the reference images for the background
    scene_descriptions = []
    if reference_image_paths:
        for ref_path in reference_image_paths:
            scene_desc = await describe_scene(ref_path)
            if scene_desc:
                scene_descriptions.append(scene_desc)
    
    scene_context = " ".join(scene_descriptions)
    if not scene_context:
        scene_context = "A clean, neutral photography studio background."

    # 3. Assemble the master prompt
    if outfit_description:
        enhanced_prompt = (
            f"A high-quality fashion editorial photograph of {outfit_description}. "
            f"The subject is located in the following environment: {scene_context}. "
            f"{prompt} "
            f"AVOID: {negative_prompt}"
        )
    else:
        enhanced_prompt = f"{prompt} AVOID: {negative_prompt}"

    project  = settings.GOOGLE_CLOUD_PROJECT
    location = settings.GOOGLE_CLOUD_LOCATION
    model    = settings.NANO_BANANA_MODEL_ID.replace("google/", "")
    endpoint = (
        f"https://{location}-aiplatform.googleapis.com/v1/projects/{project}"
        f"/locations/{location}/publishers/google/models/{model}:predict"
    )
    token = _get_access_token()

    payload = {
        "instances": [{"prompt": enhanced_prompt}],
        "parameters": {
            "sampleCount":    1,
            "aspectRatio":    "3:4",
            "outputMimeType": "image/png",
        },
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type":  "application/json",
    }

    logger.info("Calling Imagen 4 with prompt: %s", enhanced_prompt)

    async with httpx.AsyncClient(timeout=settings.GENERATION_TIMEOUT_SEC) as client:
        response = await client.post(endpoint, json=payload, headers=headers)

    if response.status_code != 200:
        logger.error("Imagen 4 API error %s: %s", response.status_code, response.text)
        raise RuntimeError(
            f"Imagen 4 generation failed [{response.status_code}]: {response.text}"
        )

    result = response.json()
    try:
        b64_image = result["predictions"][0]["bytesBase64Encoded"]
        return base64.b64decode(b64_image)
    except (KeyError, IndexError) as exc:
        raise RuntimeError(f"Unexpected Imagen 4 response: {result}") from exc


async def generate_batch(
    outfit_image_path: str,
    reference_image_paths: List[str],
    prompt: str,
    negative_prompt: str,
    count: int,
    width: int  = settings.OUTPUT_IMAGE_WIDTH,
    height: int = settings.OUTPUT_IMAGE_HEIGHT,
) -> List[Optional[bytes]]:

    results = []

    for i in range(count):
        try:
            img_bytes = await generate_image(
                outfit_image_path=outfit_image_path,
                reference_image_paths=reference_image_paths,
                prompt=prompt,
                negative_prompt=negative_prompt,
                width=width,
                height=height,
            )
            results.append(img_bytes)
            logger.info("Generated image %d/%d successfully", i + 1, count)
            if i < count - 1:
                await asyncio.sleep(3)
        except Exception as exc:
            logger.error("Image %d/%d failed: %s", i + 1, count, exc)
            results.append(None)
            await asyncio.sleep(10)

    return results