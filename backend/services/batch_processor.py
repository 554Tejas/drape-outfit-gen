"""
Batch Processor
===============
Orchestrates multi-outfit generation jobs.
- Accepts a list of outfit IDs + reference IDs
- Builds prompts for each outfit
- Calls Nano Banana 2 for each (sequentially or concurrently)
- Tracks per-image status and persists results to storage
- Updates job state throughout
"""

import asyncio
import logging
from typing import List, Optional

from models.schemas import ReferenceMeta
from services import storage, prompt_engine, nano_banana
from config import settings

logger = logging.getLogger(__name__)


async def run_batch_job(
    job_id: str,
    outfit_ids: List[str],
    reference_ids: List[str],
    images_per_outfit: int,
    custom_notes: Optional[str] = None,
) -> None:
    """
    Main batch execution coroutine.
    Runs as a background task — updates job state in storage throughout.
    """
    storage.update_job(job_id, status="processing")
    references: List[ReferenceMeta] = storage.get_references_by_ids(reference_ids)

    total_completed = 0
    total_failed = 0
    error_log = []

    for outfit_id in outfit_ids:
        outfit = storage.get_outfit(outfit_id)
        if not outfit:
            msg = f"Outfit {outfit_id} not found — skipping."
            logger.warning(msg)
            error_log.append(msg)
            total_failed += images_per_outfit
            continue

        # Build prompt for this outfit
        prompts = prompt_engine.build_prompt(
            outfit_filename=outfit.filename,
            references=references,
            custom_notes=custom_notes,
        )

        logger.info(
            "Generating %d image(s) for outfit %s (%s)",
            images_per_outfit, outfit_id, outfit.filename,
        )

        # Generate images for this outfit
        image_results = await nano_banana.generate_batch(
            outfit_image_path=outfit.upload_path,
            reference_image_paths=[r.upload_path for r in references],
            prompt=prompts["prompt"],
            negative_prompt=prompts["negative_prompt"],
            count=images_per_outfit,
        )

        for idx, img_bytes in enumerate(image_results):
            if img_bytes is not None:
                try:
                    storage.save_generated_image(
                        image_bytes=img_bytes,
                        outfit_id=outfit_id,
                        generation_index=idx,
                        prompt_used=prompts["prompt"][:500],  # truncate for storage
                    )
                    total_completed += 1
                except Exception as exc:
                    msg = f"Failed to save image {idx} for outfit {outfit_id}: {exc}"
                    logger.error(msg)
                    error_log.append(msg)
                    storage.record_failed_image(outfit_id, idx, str(exc))
                    total_failed += 1
            else:
                msg = f"Image {idx + 1} generation failed for outfit {outfit_id}"
                error_log.append(msg)
                storage.record_failed_image(outfit_id, idx, "Generation returned None")
                total_failed += 1

        # Update job progress after each outfit
        storage.update_job(
            job_id,
            completed=total_completed,
            failed=total_failed,
            error_log=error_log,
        )

    # Final job status
    import datetime
    final_status = (
        "completed" if total_failed == 0
        else ("partial" if total_completed > 0 else "failed")
    )
    storage.update_job(
        job_id,
        status=final_status,
        completed=total_completed,
        failed=total_failed,
        error_log=error_log,
        completed_at=datetime.datetime.utcnow().isoformat(),
    )
    logger.info(
        "Job %s finished — status=%s, completed=%d, failed=%d",
        job_id, final_status, total_completed, total_failed,
    )
