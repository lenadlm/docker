---
name: image-ocr
description: "Extract text from images using local OCR (Tesseract), cloud APIs, or vision models — for photos, screenshots, scanned pages, and mixed-content images."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [OCR, Tesseract, Image-Processing, Text-Extraction, Vision]
    related_skills: [pdf-documents]
---

# Image OCR — Text Extraction from Images

Extract text from standalone image files (JPEG, PNG, WebP, etc.). For PDFs, see the `pdf-documents` skill. For videos, extract frames first, then OCR.

## Critical Scoping Rule

> **OCR only on explicit user request.** Never auto-batch-process all uploaded images in a session. Users may send images for reasons other than text extraction (photos, memes, screenshots for reference, etc.). Wait for a clear directive like "transcribe this", "OCR this", "extract text from this image", or "read the text in this image".

## Decision Tree

| Image Type | Strategy | Tool |
|------------|----------|------|
| **Clean screenshot / document scan** | Direct Tesseract | `tesseract <image> stdout -l eng` |
| **Photo with text (signs, menus, screens)** | Preprocess → Tesseract | resize 2-3×, grayscale, contrast enhance, sharpen |
| **Handwritten text** | Cloud API or vision model | Claude Sonnet, GPT-4o (vision models) |
| **Complex layout / tables** | marker-pdf (works on images too) | `marker_single image.jpg --output_dir ./output` |
| **Small text / low resolution** | Upscale 2-4× (LANCZOS) + sharpen | PIL resize + ImageFilter.SHARPEN |
| **Dark/low contrast** | Autocontrast / CLAHE | PIL `ImageOps.autocontrast` or OpenCV CLAHE |

## Prerequisites

```bash
# Tesseract (fast, local, no GPU)
sudo apt-get install -y tesseract-ocr tesseract-ocr-eng

# Python libs (for preprocessing)
uv pip install Pillow

# For heavy OCR: marker-pdf (needs ~5GB for PyTorch)
# uv pip install marker-pdf
```

## Preprocessing Pipeline

When Tesseract gives poor results, apply this pipeline in order:

```python
from PIL import Image, ImageFilter, ImageEnhance, ImageOps

img = Image.open('/path/to/image.jpg')

# 1. If image is photo-like (>5K unique colors), check if text exists first
# 2. Upscale 2-3× for small text
w, h = img.size
img = img.resize((w*2, h*2), Image.LANCZOS)

# 3. Convert to grayscale
gray = img.convert('L')

# 4. Autocontrast (stretch histogram)
gray = ImageOps.autocontrast(gray, cutoff=5)

# 5. Increase contrast
enhancer = ImageEnhance.Contrast(gray)
gray = enhancer.enhance(2.0)

# 6. Sharpen
gray = gray.filter(ImageFilter.SHARPEN)

# 7. Binary threshold (for clean text on light bg)
bw = gray.point(lambda x: 0 if x < 128 else 255, '1')

# 8. Try OCR on 'gray' first, then 'bw' as fallback
gray.save('/tmp/ocr_processed.png')
```

## Tesseract Usage

```bash
# Quick test
tesseract image.jpg stdout -l eng

# With page segmentation mode
tesseract image.jpg stdout -l eng --psm 6

# Common PSM modes:
# 3  = Fully automatic (default)
# 6  = Assume uniform block of text
# 11 = Sparse text (find as much text as possible)
# 12 = Sparse text with OSD

# Multiple languages
tesseract image.jpg stdout -l eng+ara

# Save to file
tesseract image.jpg output -l eng
```

## Image Analysis (Pre-OCR)

Before OCR, check if the image actually contains text:

```python
from PIL import Image
img = Image.open('image.jpg')
print(f'Size: {img.size}')
print(f'Mode: {img.mode}')
colors = img.getcolors(maxcolors=100000)
print(f'Unique colors: {len(colors) if colors else ">100K (photo-like)"}')
# <1K colors = likely document/screenshot
# >10K colors = likely photo — may not have readable text
```

## Fallback Strategy

When local OCR fails entirely (output is noise/gibberish):

1. **Check if the image actually has text** — use vision_analyze to ask "Does this image contain readable text? What does it show?"
2. **If the active model supports vision**, delegate the text extraction to the model
3. **If the image has no text**, report that to the user
4. **If the image has text but Tesseract can't read it**, try marker-pdf or a cloud API

## Videos

For videos (MP4, MOV, etc.) that need transcription:

1. Extract audio: `ffmpeg -i video.mp4 -vn -acodec libmp3lame audio.mp3`
2. Transcribe audio: whisper, or a speech-to-text tool
3. For text visible in video frames: extract frames at intervals, then OCR

## Known Limitations

- Tesseract cannot read handwriting (use vision models or cloud APIs)
- Tesseract struggles with colored text on colored backgrounds
- Tesseract fails on very small text (<10px) — upscale first
- The current model (deepseek/deepseek-v4-flash) does not support vision — fall back to local OCR