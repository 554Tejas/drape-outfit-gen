from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
from typing import List, Optional

from models.schemas import GenerationRequest, JobResult, JobStatus
from services import storage, prompt_engine, batch_processor

router = APIRouter()


@router.post("/", response_model=JobResult)
async def start_generation(req: GenerationRequest, background_tasks: BackgroundTasks):
    for outfit_id in req.outfit_ids:
        if not storage.get_outfit(outfit_id):
            raise HTTPException(status_code=404, detail=f"Outfit {outfit_id} not found")

    if req.preview_prompts:
        references = storage.get_references_by_ids(req.reference_ids)
        previews = prompt_engine.build_batch_prompts(
            outfits=[
                {
                    "outfit_id": o,
                    "filename": storage.get_outfit(o).filename
                }
                for o in req.outfit_ids
            ],
            references=references,
            custom_notes=req.custom_prompt_notes,
        )
        return JSONResponse(content={"previews": previews})

    job_id = storage.create_job(req.outfit_ids, req.images_per_outfit)

    background_tasks.add_task(
        batch_processor.run_batch_job,
        job_id=job_id,
        outfit_ids=req.outfit_ids,
        reference_ids=req.reference_ids,
        images_per_outfit=req.images_per_outfit,
        custom_notes=req.custom_prompt_notes,
    )

    job = storage.get_job(job_id)
    job_copy = {k: v for k, v in job.items() if k != "images"}
    return JobResult(**job_copy, images=[])


@router.get("/status/{job_id}")
async def get_job_status(job_id: str):
    job = storage.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    images = []
    for outfit_id in job["outfit_ids"]:
        images.extend(storage.get_generated_images(outfit_id))

    job_copy = {k: v for k, v in job.items() if k != "images"}
    return JobResult(**job_copy, images=images)


@router.post("/regenerate")
async def regenerate(
    outfit_id: str,
    reference_ids: List[str],
    background_tasks: BackgroundTasks,
    custom_notes: Optional[str] = None,
):
    if not storage.get_outfit(outfit_id):
        raise HTTPException(status_code=404, detail="Outfit not found")

    job_id = storage.create_job([outfit_id], images_per_outfit=1)

    background_tasks.add_task(
        batch_processor.run_batch_job,
        job_id=job_id,
        outfit_ids=[outfit_id],
        reference_ids=reference_ids,
        images_per_outfit=1,
        custom_notes=custom_notes,
    )

    job = storage.get_job(job_id)
    job_copy = {k: v for k, v in job.items() if k != "images"}
    return JobResult(**job_copy, images=[])


@router.get("/preview-prompt/{outfit_id}")
async def preview_prompt(outfit_id: str, reference_ids: Optional[str] = None):
    outfit = storage.get_outfit(outfit_id)
    if not outfit:
        raise HTTPException(status_code=404, detail="Outfit not found")

    ref_id_list = reference_ids.split(",") if reference_ids else []
    references = storage.get_references_by_ids(ref_id_list)

    prompts = prompt_engine.build_prompt(
        outfit_filename=outfit.filename,
        references=references,
    )

    return {
        "outfit_id": outfit_id,
        "outfit_filename": outfit.filename,
        "prompt": prompts["prompt"],
        "negative_prompt": prompts["negative_prompt"],
    }