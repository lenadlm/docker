# OCR Debugging Workflow

Record of a session where Tesseract produced pure noise on a 1280×1252px photo-like image (23K unique colors, warm reddish tones). The image likely contained no machine-readable text.

## What Was Tried (in order)

1. **Direct tesseract** — empty/noise output
2. **List available languages** — only `eng` and `osd` loaded
3. **PSM mode 6** (uniform text block) — noise
4. **PSM mode 3** (auto) — empty
5. **2× LANCZOS upscale + grayscale + contrast 2.0 + sharpen** — noise
6. **Threshold to binary (128 midpoint)** — noise
7. **Edge detection (FIND_EDGES)** — noise
8. **Adaptive: invert dark bg, autocontrast, 3× upscale** — noise
9. **Quadrant cropping + individual OCR** — noise in every quadrant

## Lessons

- When all 4 quadrants produce equal noise, the image lacks readable text
- 23K unique colors + warm tone range → photo, not document
- Check image properties early: corner pixels, center pixel, color count
- If average pixel value > 128, it's a light-background image
- Once both `--psm 3` and `--psm 6` fail, further Tesseract config changes are unlikely to help
- At that point: use `vision_analyze` to classify the image content, or delegate to a vision-capable model

## Quick Image Classification Script

```python
from PIL import Image

img = Image.open('/path/to/image.jpg')
print(f'Size: {img.size}px')
print(f'Mode: {img.mode}')

# Corner pixels (background color clue)
corners = [
    img.getpixel((0, 0)),
    img.getpixel((img.width-1, 0)),
    img.getpixel((0, img.height-1)),
    img.getpixel((img.width-1, img.height-1)),
]
print(f'Corners: {corners}')

center = img.getpixel((img.width//2, img.height//2))
print(f'Center: {center}')

colors = img.getcolors(maxcolors=100000)
if colors:
    print(f'Unique colors: {len(colors)} → document/screenshot')
else:
    print(f'Unique colors: >100K → likely photo')

# Grayscale average
gray = img.convert('L')
pixels = list(gray.getdata())
avg = sum(pixels) / len(pixels)
print(f'Average brightness: {avg:.1f}/255')
print('Background: {}'.format('Light' if avg > 128 else 'Dark'))
```