"""
Prompt Engine
=============
Builds structured creative direction prompts for Nano Banana 2.
Optimized for Imagen 4: Focuses purely on visual descriptors rather than 
conversational instructions. The outfit description will be injected 
at the very beginning of this prompt by the generator.
"""

from typing import List, Optional, Dict
import logging
from models.schemas import ReferenceMeta, ReferenceType

logger = logging.getLogger(__name__)

OUTPUT_BLOCK = (
    "High-resolution commercial fashion photography, photorealistic, editorial quality, "
    "sharp focus on garment detail, natural skin tones, professional styling, 3:4 portrait aspect ratio."
)

def _interpret_references(
    references: List[ReferenceMeta],
    custom_notes: Optional[str] = None,
) -> str:
    """Convert uploaded reference metadata into natural-language creative direction."""
    blocks: List[str] = []

    categorized: Dict[str, List[str]] = {}
    for ref in references:
        categorized.setdefault(ref.ref_type.value, []).append(ref.filename)

    # Simplified, descriptive labels instead of conversational commands
    ref_map = {
        ReferenceType.MODEL.value:      "Model appearance matches reference",
        ReferenceType.POSE.value:       "Pose matches reference",
        ReferenceType.BACKGROUND.value: "Background setting matches reference",
        ReferenceType.LIGHTING.value:   "Lighting mood matches reference",
        ReferenceType.VIBE.value:       "Overall aesthetic matches reference",
        ReferenceType.CAMERA.value:     "Camera angle matches reference",
        ReferenceType.BRAND.value:      "Brand styling matches reference",
        ReferenceType.OTHER.value:      "Additional styling matches reference",
    }

    for ref_type, label in ref_map.items():
        if ref_type in categorized:
            blocks.append(label)

    if not blocks:
        blocks.append(
            "Clean editorial fashion photography, neutral studio or lifestyle setting, "
            "soft diffused lighting, model facing camera with confident pose"
        )

    if custom_notes:
        blocks.append(f"Styling note: {custom_notes.strip()}")

    return " ".join(blocks)


def build_prompt(
    outfit_filename: str,
    references: List[ReferenceMeta],
    custom_notes: Optional[str] = None,
) -> Dict[str, str]:
    """
    Build a creative direction prompt. 
    Note: The actual outfit description is dynamically injected at token 0 
    in nano_banana.py for maximum diffusion attention.
    """
    creative_direction = _interpret_references(references, custom_notes)

    # We only describe the scene here. The garment description is prefixed later.
    positive = f"The outfit is worn by a fashion model. {creative_direction}. {OUTPUT_BLOCK}"

    # Imagen 3/4 drop native API support for negative prompts, 
    # so we structure this to be appended as an 'AVOID' block later.
    negative = (
        "blurry, low resolution, cartoon, illustration, sketch, painting, "
        "altered outfit design, different garment colors, incorrect pattern, "
        "unrealistic proportions, extra limbs, text overlay, watermark."
    )

    logger.debug("Built prompt for outfit '%s'", outfit_filename)
    return {"prompt": positive, "negative_prompt": negative}


def build_batch_prompts(
    outfits: List[Dict],
    references: List[ReferenceMeta],
    custom_notes: Optional[str] = None,
) -> List[Dict]:
    """Build prompts for a batch of outfits."""
    results = []
    for outfit in outfits:
        prompts = build_prompt(
            outfit_filename=outfit["filename"],
            references=references,
            custom_notes=custom_notes,
        )
        results.append({
            "outfit_id":       outfit["outfit_id"],
            "filename":        outfit["filename"],
            "prompt":          prompts["prompt"],
            "negative_prompt": prompts["negative_prompt"],
        })
    return results