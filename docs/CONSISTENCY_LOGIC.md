# Outfit Consistency Logic

## Core Rule

> **The model, pose, background, lighting, and overall vibe can change. The outfit cannot.**

This is the single most important constraint in DRAPE. Every architectural decision,
every prompt block, and every API parameter exists to enforce it.

---

## Three-Layer Enforcement

Outfit consistency is enforced at **three independent layers** so that a failure at
any one layer is caught by the others.

---

### Layer 1 — Model-Level Lock (Nano Banana 2)

Nano Banana 2 accepts a dedicated `productImage` input field that is structurally
separate from the `referenceImages` list. The backend sends the outfit as:

```json
{
  "instances": [{
    "productImage": {
      "bytesBase64Encoded": "...",
      "mimeType": "image/jpeg",
      "lockGarment": true
    },
    "referenceImages": [ ... ],
    "prompt": "...",
    "negativePrompt": "..."
  }],
  "parameters": {
    "mode": "fashion_product_placement"
  }
}
```

Key flags:
- `lockGarment: true` — activates Nano Banana 2's built-in garment preservation pipeline
- `mode: "fashion_product_placement"` — tells the model to place the locked outfit into
  a generated scene rather than treating it as a style reference to be reinterpreted

This ensures the model receives the outfit as a **product constraint**, not as a
creative suggestion.

---

### Layer 2 — Prompt-Level Lock

Every generation request includes two mandatory prompt blocks that cannot be
overridden by user custom notes:

#### Positive Prompt — Outfit Lock Block

```
OUTFIT LOCK — MANDATORY PRESERVATION:
The exact outfit from the product reference image MUST be reproduced with 100% fidelity.
Preserve identically: design, silhouette, cut, color scheme, pattern, print, embroidery,
texture, fabric appearance, collar shape, neckline, sleeve style and length, cuffs,
hemline, waistline, buttons, zippers, pockets, stitching, seams, pleats, lining,
embellishments, logos, badges, and every visible garment detail. Do NOT redesign,
simplify, enhance, hallucinate, replace, or alter any aspect of the clothing.
Product accuracy is paramount.
```

This block appears **first** in the positive prompt, giving it highest semantic weight.

#### Negative Prompt — Garment Drift Prevention

```
Do NOT change: outfit design, garment color, pattern, print, embroidery, fabric texture,
collar, neckline, sleeve length or style, hemline, buttons, zippers, stitching, seams,
pleats, lining, waistband, pockets, or any structural garment detail.
Do NOT add extra logos, graphics, or text to the clothing.
Do NOT alter the outfit in any way to match a trend or improve aesthetics.
Also avoid: blurry, low resolution, cartoon, illustration, sketch, painting...
```

The negative prompt explicitly names every garment attribute that must not change,
rather than relying on a vague "keep outfit unchanged" instruction.

#### What User Notes CAN and CANNOT Do

| User Action | Affects Prompt Block | Garment Safe? |
|-------------|---------------------|---------------|
| Upload model reference | Block B (creative direction) | ✅ Yes |
| Upload background reference | Block B | ✅ Yes |
| Upload vibe/aesthetic reference | Block B | ✅ Yes |
| Add custom creative notes | Appended to Block B only | ✅ Yes |
| Modify outfit lock text | ❌ Not possible | ✅ Protected |
| Modify negative prompt | ❌ Not possible | ✅ Protected |

---

### Layer 3 — Architectural Separation

The `prompt_engine.py` module maintains a strict code-level separation:

```python
# OUTFIT_LOCK_BLOCK — hardcoded constant, never interpolated
OUTFIT_LOCK_BLOCK = """..."""

# NEGATIVE_LOCK_BLOCK — hardcoded constant, never interpolated
NEGATIVE_LOCK_BLOCK = """..."""

# Only creative direction is built from references and user input
creative_direction = _interpret_references(references, custom_notes)

positive = f"{OUTFIT_LOCK_BLOCK}\n\nCREATIVE DIRECTION:\n{creative_direction}\n\n{OUTPUT_BLOCK}"
negative = f"{NEGATIVE_LOCK_BLOCK}\n..."
```

The outfit lock constants are defined at module level and **never** accept external
input. The user's custom notes are appended to the creative direction block only —
they are structurally prevented from touching the outfit lock or negative prompt.

---

## What Can Drift (and Why)

Despite all three layers, some degree of drift is possible in edge cases:

| Garment Feature | Drift Risk | Reason |
|----------------|------------|--------|
| Solid colors | Very Low | Easy for model to preserve |
| Simple patterns (stripes, checks) | Low | Well-understood by diffusion models |
| Complex prints (photographic, illustrative) | Medium | High-frequency detail is hard to reproduce exactly |
| Fine embroidery / beading | Medium-High | Sub-pixel details may be approximated |
| Holographic / iridescent fabrics | High | Light-dependent appearance changes with scene lighting |
| Brand logos / text | Medium | Text rendering varies; Nano Banana 2 includes logo lock |

---

## Manual Review Checklist

After generation, reviewers should check each output against the original:

- [ ] Overall silhouette matches
- [ ] Color is identical (no tint shift from scene lighting)
- [ ] Pattern / print is preserved and not simplified
- [ ] Collar and neckline shape match
- [ ] Sleeve style and length match
- [ ] Hemline position matches
- [ ] Buttons, zippers, and closures are present
- [ ] Stitching and seam lines are visible where they should be
- [ ] Embellishments (embroidery, beading, patches) are present
- [ ] No extra logos or graphics added
- [ ] No fabric texture changed (e.g., denim not rendered as cotton)

Any image failing two or more checks should be regenerated.

---

## Regeneration Flow

Failed or drifted images can be regenerated individually:

```
POST /api/generate/regenerate
  { outfit_id, reference_ids, custom_notes }
```

This creates a new single-image job for the outfit, applying the same three-layer
consistency enforcement. The original images are preserved; the new image is appended
to the outfit's gallery.
