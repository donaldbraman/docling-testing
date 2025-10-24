# OCR Overlay Inspection Method

## Problem

Playwright screenshots of PDFs render as blank/black pages. Cannot directly inspect overlay PDFs.

## Solution

1. **Generate overlay PDF:**
   ```bash
   uv run python scripts/evaluation/generate_ocr_overlay.py --pdf <basename> --engine ocrmac
   ```

2. **Extract pages as PNG:**
   ```bash
   uv run python scripts/evaluation/extract_pdf_pages_as_images.py
   ```
   (Modify script to set PDF path and page numbers)

3. **Read PNG with Read tool:**
   ```python
   Read file_path=/path/to/results/ocr_engine_comparison/page_images/<pdf>_page<N>.png
   ```

## PNG images are visible in multimodal interface. PDFs are not.

## Color Legend

- Blue = TextItem (body text)
- Green = SectionHeaderItem
- Orange = ListItem
- Purple = Title
- Yellow = Caption
- Red = Footnote
- Gray = PageHeader/PageFooter

## Analysis

**No colored box = Docling completely missed this text region**
**Wrong colored box = Docling detected but misclassified**

## Key Findings - Middling Performers (89-93% recall)

**Common pattern across all 3 PDFs:**

**academic_limbo (92.9% recall, 7% loss):**
- Page 1: Entire TOC → NO BOXES (5+ entries missed)
- Missing: "Introduction...24", "I. Structural Disparities...", etc.
- Page 3: Partial paragraph detection → First 4-5 lines missing box
- Missing: "precedent to guide future cases. The timing for such reform proves especially advantageous..."

**bu_law_review_nil_compliance (89.7% recall, 10% loss):**
- Page 1: "ABSTRACT" heading → NO BOX
- Title/author captured ✓, but section header missed

**bu_law_review_learning_from_history (92.1% recall, 8% loss):**
- Page 1: Massive TOC → NO BOXES (10+ entries missed)
- Missing: All sections (I, II, III), all subsections (A, B, C), all page numbers

**All 3 PDFs:**
- Footnotes → Captured but misclassified as BLUE (should be RED)

**Pattern:**
- TOC pages → Systematic detection failure
- Regular body pages → Mostly good coverage, but academic_limbo shows partial paragraph detection issues

**Root cause:** Docling layout detection **filters out** TOC text that OCR successfully reads.

## Raw OCR vs Classified Comparison

Compared unfiltered OCR output vs Docling's classified output (academic_limbo):

**Text discarded by layout detection:**
- Characters: 3,457 (11.95% loss)
- Words: 466 (12.40% loss)
- 751 lines filtered out

**Missing TOC entries found in raw OCR:**
- "TMtroduction ......"
- "Structural Disparities in Academic Freedom Protections ........25"
- "Institutional Barriers to Student Expression Rights ...............27"
- "Oversight Boards as Constitutional Governance Reform.........29"

**Conclusion:** OCR reads TOC text correctly. Layout detection discards it during classification. Cannot fix with post-processing - text is read but then filtered out.

See `scripts/evaluation/compare_raw_ocr_vs_classified.py` for methodology.

## Configuration Testing

Tested 6 different Docling configurations on academic_limbo.

**Item counts (misleading):**
- Default: 94 items
- Keep empty clusters: 95 items (+1)

**Actual text content (definitive):**
- Character difference: +2 (+0.01%)
- Word difference: **0 (+0.00%)**
- Content added: Empty cluster with no text

**Methodology:**
```bash
# Compare actual text content, not item counts
uv run python scripts/evaluation/compare_config_text.py
```

See `scripts/evaluation/compare_config_text.py` for implementation.

**Conclusion:** Configuration tweaks cannot recover missing TOC text. Even "successful" configs added 0 words. Issue is fundamental to layout detection model.

See `docs/DOCLING_CONFIGURATION_OPTIONS.md` for full details.

## Scripts

- `scripts/evaluation/generate_ocr_overlay.py` - Generate overlays
- `scripts/evaluation/extract_pdf_pages_as_images.py` - PDF → PNG conversion
