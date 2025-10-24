# Empirical Corrections to docling_max_recall.md

**Date:** 2025-10-23
**Investigation:** Layout Detection Investigation (academic_limbo, bu_law_review_nil_compliance, bu_law_review_learning_from_history)

## Executive Summary

Through systematic testing, we discovered that **lowering the confidence threshold alone does NOT recover missing text**. The filtering mechanism is more complex than simple confidence thresholding. Additionally, **no configuration parameter changes** captured any additional text in our tests.

---

## 1. Confidence Threshold Discovery and Testing

### Finding: Threshold Parameter EXISTS but Doesn't Help

**Document's Claim (Section 2.3):**
> "there are **no explicitly documented, user-configurable parameters** to directly control the confidence threshold"

**Correction:**
The confidence threshold parameter DOES exist but is not exposed in the public API:
- Class: `docling_ibm_models.layoutmodel.layout_predictor.LayoutPredictor`
- Parameter: `base_threshold` (default: 0.3)
- Location: `LayoutPredictor.__init__()`

**Test Method:**
Monkey-patched `LayoutPredictor.__init__` to set `base_threshold=0.1` (lowering from default 0.3).

**Test Results (academic_limbo):**
```
Default threshold (0.3): 94 items, 3,292 words
Lower threshold (0.1):   94 items, 3,292 words
Difference:              +0 items, +0 words
```

**Implication:**
Confidence threshold filtering is NOT the primary (or only) mechanism causing text loss. Other filtering heuristics must be responsible.

**Evidence:**
- Script: `scripts/evaluation/test_lower_confidence_threshold.py`
- Results: `results/threshold_test/`

---

## 2. Raw OCR vs Classified Text Comparison

### Finding: OCR Reads 12.4% MORE Text Than Docling Outputs

**Document's Claim (Section 1.1):**
> "`ocrmac` is performing its function correctly and completely. It successfully identifies all textual content within the page image."

**Verification:**
CONFIRMED. We extracted raw OCR output directly and compared to Docling's classified output.

**Test Results (academic_limbo):**
```
Raw OCR output:          3,758 words, 28,933 chars
Docling classified:      3,292 words, 25,476 chars
Text LOST:               466 words (12.40%), 3,457 chars (11.95%)
Lines filtered:          751 lines
```

**Missing Content Examples (found in raw OCR, absent from Docling):**
- "TMtroduction ......"
- "Structural Disparities in Academic Freedom Protections ........25"
- "Institutional Barriers to Student Expression Rights ...............27"
- "Oversight Boards as Constitutional Governance Reform.........29"
- [All TOC entries with dotted leaders and page numbers]

**Critical Insight:**
This proves the document's core thesis: **text loss occurs during layout classification filtering, not OCR failure**.

**Evidence:**
- Script: `scripts/evaluation/compare_raw_ocr_vs_classified.py`
- Results: `results/ocr_vs_classified/`
- Missing lines: `results/ocr_vs_classified/missing_lines.txt`

---

## 3. Configuration Parameter Testing

### Finding: NO Configuration Changes Captured Additional Text

**Document's Claim (Section 2):**
Focuses on configuration as the primary approach to influence behavior.

**Test Method:**
Tested 6 different Docling configurations on academic_limbo:
1. Default (baseline)
2. `force_full_page_ocr=True`
3. Lower `bitmap_area_threshold=0.01`
4. Higher `images_scale=2.0`
5. `keep_empty_clusters=True`
6. Combined aggressive (all of the above)

**Test Results:**
```
Configuration              Items    Words    Chars
────────────────────────────────────────────────────
Default                    94       3,292    25,476
force_full_page_ocr        94       3,292    25,476
Lower bitmap threshold     94       3,292    25,476
Higher image scale         94       3,292    25,476
keep_empty_clusters        95       3,292    25,478  (+1 item, +0 words, +2 chars whitespace)
Combined aggressive        95       3,292    25,478  (+1 item, +0 words, +2 chars whitespace)
```

**Character difference (no whitespace):** 0 across all configurations

**Conclusion:**
Configuration tweaks CANNOT recover missing TOC text. The +1 item with `keep_empty_clusters` was an empty cluster containing only whitespace.

**Evidence:**
- Script: `scripts/evaluation/test_docling_configurations.py`
- Comparison: `scripts/evaluation/compare_config_text.py`
- Documentation: `docs/DOCLING_CONFIGURATION_OPTIONS.md`

---

## 4. Visual Inspection Findings

### Finding: TOC Pages Show NO Bounding Boxes (Not Misclassification)

**Method:**
Generated color-coded overlay PDFs showing Docling's text classifications.

**Visual Inspection Results:**

**academic_limbo (92.9% recall):**
- Page 1: Entire TOC → NO BOXES (all 5+ entries completely missing)
- Page 3: Partial paragraph detection → First 4-5 lines missing box

**bu_law_review_nil_compliance (89.7% recall):**
- Page 1: "ABSTRACT" heading → NO BOX

**bu_law_review_learning_from_history (92.1% recall):**
- Page 1: Massive TOC → NO BOXES (all 10+ entries, subsections, page numbers missing)

**Pattern:**
Missing text is not just misclassified (wrong color box) but completely undetected (no box at all).

**Evidence:**
- Script: `scripts/evaluation/generate_ocr_overlay.py`
- Script: `scripts/evaluation/extract_pdf_pages_as_images.py`
- Overlays: `results/ocr_engine_comparison/overlays/`
- Page images: `results/ocr_engine_comparison/page_images/`
- Documentation: `docs/OCR_OVERLAY_INSPECTION_GUIDE.md`

---

## 5. Filtering Mechanisms Beyond Confidence Threshold

### Finding: Multiple Filtering Mechanisms Likely at Play

**Document's Hypothesis (Section 1.3):**
Lists 3 mechanisms:
1. Confidence thresholding
2. Overlap resolution
3. Intersection and grouping

**Empirical Evidence:**
Since lowering confidence threshold to 0.1 captured +0 words, one or more of the following must be responsible:
- **Overlap resolution heuristics** (prefer larger boxes, certain labels)
- **Minimum size thresholds** (TOC text may be in small boxes)
- **Semantic pattern rejection** (dotted leaders, right-aligned page numbers)
- **Special layout rules** (TOC formatting doesn't match expected patterns)

**Hypothesis:**
TOC text has unique formatting patterns (dotted leaders, mixed alignment, variable spacing) that don't match the layout model's learned patterns for "body text", "header", or "footnote". The classification stage may be rejecting these as "low quality" or "ambiguous" regardless of confidence score.

---

## 6. Code Issues in Programmatic Solution (Section 3.3)

### Finding: Bounding Box Conversion Has Bugs

**Document's Code (lines 279-282):**
```python
x1 = box
y1 = box
x2 = box + box
x2 = box + box
```

**Correction Needed:**
```python
x1 = box[0] / img_width
y1 = box[1] / img_height
x2 = (box[0] + box[2]) / img_width
y2 = (box[1] + box[3]) / img_height
```

**Note:** ocrmac box format is `[x, y, width, height]` in pixels, needs conversion to normalized `[x1, y1, x2, y2]` for Docling.

---

## Recommendations for Document Updates

### Section 1.3: Update Confidence Threshold Mechanism
**Add empirical test result:**
> "However, empirical testing shows that lowering the base_threshold from 0.3 to 0.1 captures zero additional words, indicating that confidence filtering is not the primary mechanism responsible for text loss in TOC pages."

### Section 2.3: Update Available Parameters
**Replace "no parameters" with:**
> "The `LayoutPredictor` class contains a `base_threshold` parameter (default: 0.3) that controls confidence filtering, but it is not exposed in the public API. Monkey-patching tests show that lowering this threshold to 0.1 does not recover missing text, suggesting the filtering is more complex than simple confidence thresholding."

### Section 2: Add Empirical Configuration Testing
**Add new subsection after 2.3:**
> "### 2.4 Empirical Testing Results
>
> Systematic testing of 6 different configurations (force_full_page_ocr, lower bitmap thresholds, higher image scale, keep_empty_clusters, combined aggressive) on academic_limbo showed zero word improvement across all configurations. The only change observed was +1 empty cluster with +2 whitespace characters. This confirms that configuration alone cannot recover the ~12% of text lost during layout classification."

### Section 3.3: Fix Code and Add Raw OCR Comparison
**Before programmatic reconciliation, add:**
> "Comparative analysis shows that raw OCR output contains 12.4% more words than Docling's classified output. All missing TOC entries (e.g., 'Introduction......24', 'Structural Disparities...25') are present in the raw OCR but absent from Docling's final output. This confirms that the reconciliation approach is necessary and viable."

---

## Supporting Documentation

- **Investigation Summary:** `docs/LAYOUT_DETECTION_INVESTIGATION_SUMMARY.md`
- **Overlay Inspection Method:** `docs/OCR_OVERLAY_INSPECTION_GUIDE.md`
- **Configuration Options:** `docs/DOCLING_CONFIGURATION_OPTIONS.md`

---

*Investigation completed: 2025-10-23*
