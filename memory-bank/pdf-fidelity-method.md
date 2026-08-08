# PDF Visual-Fidelity Method — MANDATORY for any "match this document" task

_Standing rule (permanent). Added 2026-08-08 after a document was rejected
twice because I compared PDFs with plain text extraction only and reported
"identical" while the DESIGN differed. Never repeat this. Do not wait to be
reminded — this is the default procedure whenever a task is "copy / match /
reproduce this PDF exactly," or whenever a user says my output "isn't
identical."_

## Why text extraction is NOT enough

`pdfplumber.extract_text()` (and any plain-text dump) is BLIND to everything
that actually makes a document look right: font family, **size**, **bold/
italic**, x/y **position**, **alignment** (left/center/right/justified),
indents, and inter-word/letter spacing. It can also silently merge or drop
words. Reporting "all lines identical" from text alone is meaningless for a
design match and must never be presented as proof of fidelity.

## The required procedure (do ALL of it)

Tools are available in this environment: `pip install pymupdf` (renders
without poppler; poppler/pdftoppm is NOT installed).

1. **RENDER BOTH PDFs TO IMAGES AND LOOK AT THEM.**
   ```python
   import pymupdf
   pix = pymupdf.open(path)[0].get_pixmap(matrix=pymupdf.Matrix(2,2))
   pix.save("out.png")
   ```
   Then actually open/view both PNGs (I can see images) and compare side by
   side. This is the single most important step and catches ~everything.

2. **GEOMETRIC DIFF — compare per-span/per-word geometry, not just text.**
   Extract `(text, x0, baseline_y, size, bold, italic)` for every span and
   compare against the target with tolerances (≈±2.5pt x, ±1.5pt y; size and
   bold/italic must match exactly):
   ```python
   d = pymupdf.open(path)[0].get_text("dict")
   # span["origin"] = (x, baseline_y); span["size"]; span["flags"] & 16 = bold, & 2 = italic
   ```
   For robustness against line-grouping artifacts, also compare word boxes:
   `page.get_text("words")` → `(x0,y0,x1,y1,text)`, match by text+position.
   Font-metric drift of a few pt on a long ragged line is expected when the
   target embeds a font (e.g. Times New Roman) and I use base-14 Times —
   note it, don't chase it; but ANY difference in alignment, size, weight,
   indent, or block position is a real defect to fix.

3. **Only after render + geometry agree**, deliver. State that fidelity was
   verified by rendering and geometric diff, not text.

## What I missed last time (the specific failure modes to always check)

- **Title alignment**: centered vs right- vs left-aligned. (V4 centers
  "BID PROPOSAL"; I had right-aligned it AND left a stray date on the line.)
- **Block indents**: the To/From contact block is indented (labels at
  x≈87), not at the left margin.
- **Per-line font SIZE**: RE line is 12pt; terms paragraph is 10pt; name
  line is **8pt**; body 10.5. Sizes vary line to line — verify each.
- **Weight**: the RE/Job-Number line and the signature name line are BOLD.
- **Centered sub-lines**: "Please sign, date, and return." is centered.
- **Leading spaces inside a span** shift the visible x (V4's "Job Number:"
  span origin was 303.5 but visible text began at 318.5 after padding).

## Reusable builder

`build_bid_v4match.py` (scratchpad + 26-4509 Drive folder) reproduces the
approved V4 bid at absolute coordinates with V4's own line breaks. It is the
template for pixel-faithful regeneration; adapt its measured coordinate table
for other documents rather than re-deriving layout by feel.
