# Docling Scaling Test Results

**Test Document:** Jackson_2014.pdf (6.6 MB, 83 pages)
**Hardware:** M1 Pro MacBook, 32GB RAM, MPS acceleration
**Date:** 2025-10-13

---

## Processing Times

| Scale | Time (sec) | Time (min) | Speed vs 1x |
|-------|-----------|------------|-------------|
| **1.0x** | 238 | ~4.0 min | Baseline |
| **2.0x** | 205 | ~3.4 min | **14% faster!** |
| **3.0x** | ⏳ Running | ... | ... |

**Surprising finding:** 2x was actually faster than 1x!

Possible explanations:
- Model caching/warmup effects
- 2x resolution hits a "sweet spot" for the layout model
- Background processes interference on 1x run

---

## Output Quality (Preliminary)

### Markdown Files Generated:
- ✅ `Jackson_2014_scale_1.0x.md` (375 KB)
- ✅ `Jackson_2014_scale_2.0x.md` (375 KB)
- ⏳ `Jackson_2014_scale_3.0x.md` (pending)

### Text Quality Observations:

**Footnotes:** Present in output (numbered 1, 2, 3...) mixed with body text
**Hyphenation:** Line-break hyphens still present
**Structure:** Reading order preserved, paragraphs maintained

### Sample Footnotes Found in Output:
```
7. See STEPHEN BREYER, ACTIVE LIBERTY...
8. 132 S. Ct. 2537 (2012).
9. See id. at 2551-52 (Breyer, J., concurring)
10. 554 U.S. 570 (2008).
```

---

## Critical Question: Layout Detection

**Status:** ✅ **BREAKTHROUGH - FOOTNOTES ARE DETECTED!**

With `generate_parsed_pages=True`, Docling successfully provides labeled elements via `doc.iterate_items()`:

**Jackson_2014.pdf Label Distribution:**
- ✅ **205 footnotes** detected and labeled
- ✅ **261 text blocks**
- ✅ **32 section headers**
- ✅ **272 list items**
- ✅ **5 pictures**
- ✅ **1 document index**

**Key Finding:** The labels are accessible through `document.body` using `doc.iterate_items()`, NOT through `result.pages.predictions`.

**This means:** We CAN programmatically filter footnotes!

**Testing now:** `extract_body_only.py` to extract clean body text without footnotes

---

## Configuration Used

```python
pipeline = PdfPipelineOptions(
    layout_options=LayoutOptions(),  # Heron model
    generate_parsed_pages=True,      # Enable bbox detection
    generate_page_images=True,       # Visual verification
    images_scale=1.0 / 2.0 / 3.0,    # Variable scaling
    do_table_structure=True,
    table_structure_options=dict(
        mode=TableFormerMode.ACCURATE,
        do_cell_matching=False
    ),
    do_ocr=True,
)
```

---

## Comparison With Other Methods

| Method | Speed | Cost | Footnotes | Hyphenation |
|--------|-------|------|-----------|-------------|
| **Docling 1x** | 4 min | $0 | ❓ TBD | ❌ Not fixed |
| **Docling 2x** | 3.4 min | $0 | ❓ TBD | ❌ Not fixed |
| **Spatial (12FA)** | 9 sec | $0 | ✅ Removed | ❌ Not fixed |
| **Gemini Flash** | 5-10 sec | $0.065 | ✅ Can remove | ❌ Not fixed |
| **Gemini Pro** | 10-15 sec | $0.26 | ✅ Can remove | ✅ Fixed |

---

## Key Findings So Far

1. **Speed**: Docling is 15-30x slower than alternatives
2. **Quality**: Full text extraction, but footnotes remain
3. **Surprise**: 2x scaling was faster than 1x
4. **Critical test pending**: Bounding box inspection

---

## Next Steps

1. ⏳ **Wait for 3x to complete**
2. **Run `inspect_boxes.py`** to find bounding box data structure
3. **Analyze labeled boxes** - how many footnotes detected?
4. **If bounding boxes work:**
   - Write filter to extract body text only
   - Compare quality vs other methods
   - Test on full corpus
5. **If bounding boxes don't work:**
   - Docling not suitable for your use case
   - Stick with spatial detection + Flash cleanup

---

## Bottom Line (Preliminary)

**Docling works** for full text extraction with good structure preservation.

**Critical question unanswered:** Can it identify footnotes as separate elements we can filter out?

**Answer pending:** Bounding box inspection when all tests complete.
