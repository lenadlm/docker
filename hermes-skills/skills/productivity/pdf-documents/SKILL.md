---
name: pdf-documents
description: "Work with PDFs and documents — extract text (pymupdf/marker-pdf), edit text/typos (nano-pdf CLI), split/merge/search, OCR scanned documents."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [PDF, Documents, OCR, Text-Extraction, nano-pdf, pymupdf, marker-pdf, Editing]
    related_skills: [powerpoint, image-ocr]
---

# PDF & Document Manipulation

Extract, edit, split, merge, and search PDFs. For PowerPoint (PPTX), see the `powerpoint` skill. For DOCX, use `python-docx` (parses actual document structure — better than OCR).

**For standalone images (JPEG, PNG, WebP, etc.)** — see the `image-ocr` skill. This skill covers PDFs only.

## Decision Tree

| Task | Tool | When |
|------|------|------|
| Text extraction from text-based PDF | pymupdf | Most common — fast, lightweight (~25MB) |
| Scanned PDF / OCR | marker-pdf | Needs PyTorch (~3-5GB) — for scans, equations, complex layouts |
| Edit text/typos/titles in PDF | nano-pdf | Natural-language instructions |
| Split pages / merge PDFs | pymupdf | Built-in, no extra deps |
| Text search across PDF | pymupdf | Built-in search_for() |

### First: Try web_extract for URLs
If the document has a URL, always try `web_extract` first — handles PDF-to-markdown via Firecrawl with no local dependencies:
```bash
web_extract(urls=["https://arxiv.org/pdf/2402.03300"])
```

---

## nano-pdf — Natural Language PDF Editing

Edit PDFs using natural-language instructions. Point at a page and describe what to change.

### Prerequisites
```bash
uv pip install nano-pdf
```

### Usage
```bash
nano-pdf edit <file.pdf> <page_number> "<instruction>"
```

### Examples
```bash
# Change a title
nano-pdf edit deck.pdf 1 "Change the title to 'Q3 Results' and fix the typo in the subtitle"
# Update a date
nano-pdf edit report.pdf 3 "Update the date from January to February 2026"
# Fix content
nano-pdf edit contract.pdf 2 "Change the client name from 'Acme Corp' to 'Acme Industries'"
```

### Notes
- Page numbers may be 0-based or 1-based depending on version — retry with ±1 if wrong page hits
- Uses an LLM under the hood (needs API key)
- Works for text changes; complex layout modifications may need a different approach

---

## pymupdf — Lightweight Text Extraction

### Installation
```bash
pip install pymupdf pymupdf4llm
```

### Basic text extraction
```bash
python3 -c "
import pymupdf
doc = pymupdf.open('document.pdf')
for page in doc:
    print(page.get_text())
"
```

### Markdown output
```python
import pymupdf4llm
md_text = pymupdf4llm.to_markdown("document.pdf")
```

### Split pages
```python
import pymupdf
doc = pymupdf.open("report.pdf")
new = pymupdf.open()
for i in range(5):
    new.insert_pdf(doc, from_page=i, to_page=i)
new.save("pages_1-5.pdf")
```

### Merge PDFs
```python
import pymupdf
result = pymupdf.open()
for path in ["a.pdf", "b.pdf", "c.pdf"]:
    result.insert_pdf(pymupdf.open(path))
result.save("merged.pdf")
```

### Search for text
```python
import pymupdf
doc = pymupdf.open("report.pdf")
for i, page in enumerate(doc):
    results = page.search_for("revenue")
    if results:
        print(f"Page {i+1}: {len(results)} match(es)")
        print(page.get_text("text"))
```

### Extract images
```python
import pymupdf
doc = pymupdf.open("document.pdf")
for i, page in enumerate(doc):
    for img in page.get_images():
        xref = img[0]
        base_image = doc.extract_image(xref)
        with open(f"image_{i}_{xref}.png", "wb") as f:
            f.write(base_image["image"])
```

---

## marker-pdf — High-Quality OCR

For scanned documents, equations, forms, and complex layout analysis.

### Prerequisites
```bash
# Check disk space first — needs ~5GB for PyTorch + models
pip install marker-pdf
```

### Usage
```bash
# Single file to markdown
marker_single document.pdf --output_dir ./output

# Batch process folder
marker /path/to/folder --workers 4

# OCR scanned document (auto-detected)
marker_single scanned_document.pdf --output_dir ./output
```

### When to use
- **Scanned PDFs** — pymupdf returns nothing for scans; marker handles OCR in 90+ languages
- **Equations/LaTeX** — marker extracts them, pymupdf does not
- **Complex layouts** — marker detects reading order, headers/footers
- **Tables** — marker has high-accuracy table extraction
- **Code blocks** — marker preserves code formatting

### Speed
- **CPU**: ~1-14s/page
- **GPU**: ~0.2s/page
- First run downloads ~2.5GB of models to `~/.cache/huggingface/`

### Notes
- marker-pdf downloads models on first use
- If disk space is tight, use pymupdf for text-based PDFs and only install marker for scanned docs
- For Word docs (.docx): `pip install python-docx` (far better than any PDF approach)
- For PowerPoint (.pptx): see the `powerpoint` skill