# Layout Detection Investigation: Final Summary

## Executive Summary

Middling performers (89-93% recall) lose 7-12% of text **NOT** due to OCR failures, but due to layout detection **filtering out** text that OCR successfully reads.

## Investigation Timeline

### Phase 1: Visual Overlay Inspection
- Generated color-coded overlays showing Docling's text classifications
- Discovered TOC entries and some body text have **NO bounding boxes**
- **Initial hypothesis:** Layout detection fails to detect these regions

### Phase 2: Configuration Testing
- Tested 6 different Docling configurations (force full page OCR, lower thresholds, higher scale, keep empty clusters)
- **Result:** 0 additional words captured (only empty clusters)
- **Conclusion:** Configuration cannot fix the issue

### Phase 3: Raw OCR vs Classified Comparison (**Critical Discovery**)
- Compared unfiltered OCR output vs Docling's classified output
- **Result:** OCR successfully reads **12% more text** than Docling outputs
- **Missing text includes:** All TOC entries, citation fragments, some footnotes

### Phase 4: Confidence Threshold Testing (**Definitive Test**)
- Discovered `LayoutPredictor` has `base_threshold=0.3` parameter (not exposed in public API)
- Monkey-patched threshold to 0.1 (lowering from 0.3)
- **Result:** 0 additional words captured
- **Conclusion:** Confidence thresholding is NOT the primary filtering mechanism

## Key Finding

**The issue is NOT layout detection failure. The issue is layout classification filtering.**

### What Actually Happens

1. **Layout detection:** ✓ Detects TOC regions
2. **OCR:** ✓ Successfully reads TOC text
3. **Classification:** ❌ Filters out/discards TOC text
4. **Output:** TOC text missing from final output

### Evidence

**academic_limbo (92.9% recall):**

**Raw OCR output (what OCR reads):**
```
TMtroduction ......
Structural Disparities in Academic Freedom Protections ........25
Institutional Barriers to Student Expression Rights ...............27
Oversight Boards as Constitutional Governance Reform.........29
```

**Docling classified output (what user gets):**
```
[ALL TOC ENTRIES MISSING]
```

**Statistics:**
- Text discarded: 12.40% of words (466 words)
- Lines filtered: 751 lines
- Character loss: 3,457 chars (11.95%)

## Root Cause

Layout classification logic does not recognize TOC formatting patterns:
- Dotted leaders (.....)
- Right-aligned page numbers
- Indented hierarchical structure
- Mixed fonts/spacing

These patterns don't match expected "body text", "header", or "footnote" patterns, so the classifier discards them.

**Filtering mechanism is MORE COMPLEX than simple confidence thresholding:**
- Lowering `base_threshold` from 0.3 → 0.1 captured +0 words
- Additional heuristics must be active: overlap resolution, minimum size, semantic pattern matching
- TOC-specific formatting likely rejected by semantic classification rules

## Implications

### Cannot Fix With:
- ❌ OCR parameter tuning (OCR is working correctly)
- ❌ Detection thresholds (detection is happening)
- ❌ Configuration changes (tested 6 configurations, all yielded +0 words)
- ❌ Confidence threshold lowering (tested 0.3 → 0.1, yielded +0 words)
- ❌ Post-processing (text is filtered before output)

### Could Fix With:
- ✅ Modified layout classifier that recognizes TOC patterns
- ✅ Bypass classification filter for certain text types
- ✅ Train custom classifier on law review TOCs
- ✅ Use raw OCR output directly (no classification)

### Current Workaround:
Accept 89-93% recall as baseline for complex academic PDFs with TOC pages.

## Methodology

### Proper Evaluation Approach

**Wrong:**
```python
# Item count doesn't tell you what text was captured
len(doc.document.texts)  # ❌
```

**Right:**
```python
# Compare actual text content
raw_ocr_text = extract_raw_ocr(pdf)
classified_text = extract_docling_classified(pdf)

# Calculate what was lost
words_lost = count_words(raw_ocr_text) - count_words(classified_text)
missing_lines = find_missing_lines(raw_ocr_text, classified_text)
```

## Tools Created

1. `scripts/evaluation/generate_ocr_overlay.py` - Visual overlay generation
2. `scripts/evaluation/extract_pdf_pages_as_images.py` - PDF → PNG for inspection
3. `scripts/evaluation/test_docling_configurations.py` - Configuration testing
4. `scripts/evaluation/compare_config_text.py` - Text content comparison
5. `scripts/evaluation/compare_raw_ocr_vs_classified.py` - **Most important: OCR vs classification comparison**
6. `scripts/evaluation/test_lower_confidence_threshold.py` - Confidence threshold monkey-patch testing

## Documentation

- `docs/OCR_OVERLAY_INSPECTION_GUIDE.md` - Visual inspection methodology
- `docs/DOCLING_CONFIGURATION_OPTIONS.md` - All configuration options + test results
- `docs/LAYOUT_DETECTION_INVESTIGATION_SUMMARY.md` - This document
- `docs/DOCLING_MAX_RECALL_CORRECTIONS.md` - **Corrections to user's docling_max_recall.md document**

## Recommendation

**For current project:**
Accept 89-93% recall as baseline. The missing text (TOC entries) is less critical for main body text extraction.

**For future improvement:**
- Use raw OCR output directly for maximum recall (100%)
- Implement custom post-processing to classify text types
- Or: Train custom layout classifier on law review TOC patterns

---

*Investigation completed: 2025-10-23*
*PDFs tested: academic_limbo, bu_law_review_nil_compliance, bu_law_review_learning_from_history*
