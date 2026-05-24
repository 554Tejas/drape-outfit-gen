# Sample Data — Testing Guide

This folder contains sample input/output examples for testing and demonstrating DRAPE.

## Folder Structure

```
sample_data/
├── outfits/          ← Upload these as outfit images
├── references/       ← Upload these as reference images  
└── outputs/          ← Expected-style output examples
```

## Recommended Test Images

### Outfit Images (sample_data/outfits/)

For best results, use:
- **Flat-lay shots**: Garment laid flat on white/light background
- **Ghost mannequin**: Invisible mannequin with clean studio background  
- **Simple model shot**: Front-facing, neutral pose, clean background

Recommended sources for test images:
- Your own product catalog images
- License-free fashion images from [Unsplash](https://unsplash.com/s/photos/fashion-product)
- Flat-lay stock photos from [Pexels](https://www.pexels.com/search/clothing%20flat%20lay/)

**Naming convention for testing:**
```
outfits/
├── white-linen-dress-SKU001.jpg
├── navy-blazer-SKU002.png
├── floral-midi-skirt-SKU003.jpg
└── black-turtleneck-SKU004.jpg
```

### Reference Images (sample_data/references/)

Organize by reference type to test the classification system:

```
references/
├── model/
│   ├── editorial-model-ref.jpg     (tall, confident, editorial look)
│   └── lifestyle-model-ref.jpg    (relaxed, natural, lifestyle feel)
│
├── background/
│   ├── urban-street-bg.jpg        (city sidewalk, golden hour)
│   ├── studio-white-bg.jpg        (clean white studio)
│   └── nature-garden-bg.jpg       (lush green garden setting)
│
├── lighting/
│   ├── golden-hour-light.jpg      (warm, directional, soft)
│   └── studio-light.jpg           (diffused, even, commercial)
│
├── vibe/
│   ├── minimalist-editorial.jpg   (clean, high-fashion vibe)
│   └── boho-lifestyle.jpg         (relaxed, earthy, bohemian)
│
└── pose/
    ├── power-pose.jpg             (confident, structured stance)
    └── candid-walk.jpg            (natural movement, candid feel)
```

---

## Test Workflow

### Test 1 — Single Outfit, Single Reference

1. Upload `outfits/white-linen-dress-SKU001.jpg` as outfit
2. Upload `references/background/studio-white-bg.jpg` as `background` reference
3. Generate 2 images
4. Verify: dress design, color, and fabric are identical to source

### Test 2 — Batch via ZIP

1. Create a ZIP containing 3–5 outfit images
2. Upload via **Upload → ZIP Archive**
3. Upload 2–3 reference images of different types
4. Generate 2 images per outfit
5. Check gallery — should show one group per outfit

### Test 3 — Prompt Preview

1. Upload one outfit + two references (different types)
2. Go to **Generate** tab
3. Click **Preview Prompt** before generating
4. Verify: outfit lock block appears first in the positive prompt
5. Verify: negative prompt contains all garment attribute prohibitions

### Test 4 — Google Drive Folder

1. Create a Google Drive folder and upload 3 outfit images to it
2. Set folder sharing to "Anyone with link can view"
3. In the Upload tab, paste the folder URL under **Google Drive → Outfits**
4. Verify all images are ingested and appear in the outfit list

### Test 5 — Regeneration

1. Complete any generation job
2. In the Gallery, find a generated image
3. Click **Regenerate** on that outfit
4. Verify: new image appears alongside the original

---

## Expected Output Quality

Generated images should:
- ✅ Show the exact outfit from the reference
- ✅ Use the model type / pose / background / lighting from references
- ✅ Look commercially usable (sharp, well-lit, professional)
- ✅ Be at 1024×1365px (3:4 portrait ratio)
- ❌ NOT change any garment detail from the source outfit
