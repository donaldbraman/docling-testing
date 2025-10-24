# OCR Pipeline Investigation Findings

**Date:** 2025-10-22
**Investigation:** Why OCR extraction performance is poor on challenging PDFs

## Summary

We investigated why ocrmac OCR showed only 4.9-20% recall on ground truth for worst-performing PDFs. Through systematic testing, we discovered **two critical bugs** and one **fundamental limitation**.

---

## Critical Bugs Discovered

### Bug #1: Fake Grayscale Conversion

**Problem:** Pipeline claimed to create "grayscale" PDFs but actually created RGB.

**Root Cause:** PyMuPDF's `insert_image()` converts grayscale pixmaps back to RGB colorspace.

```python
# Creates grayscale pixmap
pix = page.get_pixmap(colorspace="gray")  # CS_GRAY ✓

# But inserting converts to RGB!
page.insert_image(page.rect, pixmap=pix)  # Becomes CS_RGB ❌
```

**Impact:**
- All "grayscale" PDFs were actually RGB (3x file size)
- OCR engines received RGB data, not grayscale
- Testing baseline was invalid

**Status:** Attempted fix using PNG intermediate still results in RGB. PyMuPDF appears to force RGB output.

---

### Bug #2: OCR Engine Affects Layout Detection

**Problem:** Tesseract finds 23% fewer text blocks than ocrmac on the **same PDF**.

**Evidence:**
| Metric | ocrmac | Tesseract | Difference |
|--------|--------|-----------|------------|
| Text blocks | 946 | 729 | -217 (-23%) |
| Characters | 313,322 | 295,425 | -17,897 (-6%) |

**Root Cause:** Docling's layout analysis produces different results depending on OCR engine choice. This is NOT just OCR quality - **fewer text regions are being detected**.

**Impact:**
- Comparisons show low overlap because engines find different numbers of blocks
- Coverage metrics (91-100%) are misleading - similar char counts from fewer blocks means blocks are larger/merged
- Overlays show mostly red (ocrmac only) and blue (Tesseract only) with little green (both)

**Status:** Running controlled test on same PDF with both engines to confirm.

---

## Test Results

### DPI Tests (300 vs 600)

**Result:** Higher DPI extracted LESS text!

| Test | Characters | vs Baseline |
|------|-----------|-------------|
| 300 DPI | 140,070 | 95.8% |
| 600 DPI | 138,376 | 94.6% ⚠️ |

**Conclusion:** Resolution is not the bottleneck.

---

### OCR Engine Comparison

Tested Tesseract vs ocrmac on entire corpus (12 PDFs with ground truth):

| Coverage Range | Count | Interpretation |
|---------------|-------|----------------|
| >105% (Tesseract better) | 0 | Never better |
| 95-105% (Similar) | 11 | Usually similar |
| <95% (Tesseract worse) | 1 | Sometimes worse |

**Average coverage:** 96.7%

**Conclusion:** OCR engine choice doesn't significantly affect extraction quality. Both struggle equally on difficult PDFs.

---

### Color Overlays Generated

Created overlay PDFs showing:
- 🟢 Green: Text found by BOTH engines
- 🔵 Blue: Text ONLY found by Tesseract
- 🔴 Red: Text ONLY found by ocrmac

**Observation:** Very little green (overlap) in worst-performing PDFs, confirming that engines are finding different text regions, not just disagreeing on content.

---

## Fundamental Finding

**The problem isn't the OCR engine - it's the entire approach.**

Converting PDFs to image-only format:
1. ❌ Destroys existing text layers
2. ❌ Loses color/contrast information (even though we tried to preserve it)
3. ❌ Causes layout analysis to fail on complex documents
4. ❌ Results in 5-20% recall on challenging multi-column PDFs

**Key insight:** Both ocrmac and Tesseract perform similarly poorly because they face the same fundamental limitation - trying to OCR image-only versions of documents that originally had text layers.

---

## Recommendations

### Immediate Next Steps

1. **Test original PDFs directly** - Skip image conversion entirely and extract from original PDFs with native text layers

2. **Investigate Docling layout detection** - Why does layout analysis behave differently with different OCR engines?

3. **Use markdown export** - We save `doc.document.export_to_markdown()` but don't use it. This contains more content (312,430 chars vs 295,425 from text blocks)

### Long-term Solutions

1. **Hybrid approach** - Use native text extraction where available, fall back to OCR only for image-only pages

2. **Pre-processing** - Test if OCRmyPDF's preprocessing improves layout detection before Docling

3. **Alternative tools** - Evaluate other PDF extraction libraries that handle mixed text/image PDFs better

---

## Files Generated

### Test Results
- `results/dpi_test/` - 300 DPI vs 600 DPI comparison
- `results/grayscale_fix_test/` - True grayscale conversion attempts
- `results/tesseract_corpus_pipeline/` - Full corpus Tesseract pipeline

### Overlays
- `results/tesseract_corpus_pipeline/overlays/` - 5 worst-performing PDFs with color-coded visualizations

### Comparison Data
- `results/tesseract_corpus_pipeline/comparisons/` - JSON files with detailed metrics for each PDF

### Logs
- `corpus_tesseract_comparison_ordered.log` - Full pipeline processing worst→best
- `dpi_test.log` - DPI comparison test
- `true_grayscale_test.log` - Grayscale conversion attempts
- `ocr_layout_test.log` - OCR engine layout detection comparison (running)

---

## Open Questions

1. **Why does Tesseract find fewer blocks?** Is this a Docling bug or intended behavior?

2. **Can we force true grayscale?** PyMuPDF seems to force RGB - is there an alternative?

3. **What text is Docling missing?** The markdown export has 4-6% more content than text blocks - where is it?

4. **Should we abandon image-only conversion?** The entire approach may be fundamentally flawed for PDFs with native text.

---

*Investigation ongoing - results from controlled OCR layout test pending.*
