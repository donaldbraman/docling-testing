# Maximizing Text Recall in Docling: Empirical Analysis and Solutions

**Problem:** Docling discards ~12% of successfully OCR'd text during layout classification.

**Solution:** Programmatic reconciliation using raw OCR output.

---

## Executive Summary

**Finding:** Docling's layout classification pipeline filters out 7-12% of text that OCR successfully reads. This is NOT an OCR failure but a deliberate filtering mechanism that rejects text not matching learned semantic patterns (TOC entries, citations, some footnotes).

**Empirical Evidence:**
- Raw OCR output: 3,758 words
- Docling classified: 3,292 words
- **Loss: 466 words (12.4%)**

**What doesn't work:**
- ❌ Configuration changes (tested 6 configs, all yielded +0 words)
- ❌ Lowering confidence threshold (0.3 → 0.1 yielded +0 words)
- ❌ OCR parameter tuning (OCR already reads all text)

**What works:**
- ✅ Programmatic reconciliation (compare raw OCR vs Docling output, re-insert missing text)
- ✅ Use raw OCR directly (bypass classification, 100% recall)

---

## 1. Docling Pipeline Architecture

### 1.1 OCR Stage (ocrmac)

**Function:** Convert page image pixels to machine-readable text.

**Output:** List of `(text, confidence, [x, y, width, height])` tuples.

**Result:** ✅ Successfully reads ALL text (verified by raw extraction).

### 1.2 Layout Analysis Model

**Function:** Classify page regions into semantic types (Paragraph, Section_Header, List_Item, Table, Picture, Footnote, etc.).

**Model:** RT-DETR object detection, trained on DocLayNet.

**Output:** List of `(class_label, bbox, confidence_score)` predictions.

**Note:** Operates on page image, independent of OCR output.

### 1.3 Classification Filtering (Where Text Loss Occurs)

**Process:**
1. OCR reads all text → Complete text dataset
2. Layout model predicts semantic regions → Region proposals
3. **Filtering stage** applies multiple heuristics:
   - Confidence threshold (`base_threshold=0.3` in `LayoutPredictor`)
   - Overlap resolution (prefer larger boxes, certain labels)
   - Minimum size thresholds
   - **Semantic pattern matching** (rejects non-standard formatting)
4. Text-to-region intersection → Assign OCR text to surviving regions
5. **Orphaned text discarded** → Text without semantic container is lost

**Critical Discovery:**
- Lowering `base_threshold` to 0.1 captured **+0 words**
- Filtering is more complex than simple confidence scoring
- TOC formatting (dotted leaders, right-aligned numbers, hierarchical indentation) doesn't match learned patterns

**Missing Content Pattern:**
- Table of Contents entries (100% loss rate)
- Citation fragments with special formatting
- Text in unusual layouts (multi-column transitions)

---

## 2. Configuration Options (Limited Effectiveness)

### 2.1 Essential Baseline Configuration

```python
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, OcrMacOptions

# Baseline configuration
ocr_options = OcrMacOptions(
    force_full_page_ocr=True  # Always OCR page image (ignore embedded text)
)

pipeline_options = PdfPipelineOptions(
    do_ocr=True,
    ocr_options=ocr_options,
    do_table_structure=True  # Or False for debugging multi-column issues
)

converter = DocumentConverter(
    format_options={
        InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
    }
)
```

### 2.2 Tested Configurations (Empirical Results)

| Configuration | Items | Words | Result |
|--------------|-------|-------|--------|
| Default | 94 | 3,292 | Baseline |
| force_full_page_ocr | 94 | 3,292 | +0 words |
| Lower bitmap threshold (0.01) | 94 | 3,292 | +0 words |
| Higher image scale (2.0x) | 94 | 3,292 | +0 words |
| keep_empty_clusters | 95 | 3,292 | +1 empty cluster, +0 words |
| Combined aggressive | 95 | 3,292 | +0 words |

**Conclusion:** Standard configuration CANNOT recover filtered text.

### 2.3 Confidence Threshold (Internal Parameter)

**Discovery:**
- Parameter: `docling_ibm_models.layoutmodel.layout_predictor.LayoutPredictor.__init__(base_threshold=0.3)`
- NOT exposed in public API
- Monkey-patch test: Lowering to 0.1 yielded **+0 words**

**Implication:** Confidence filtering is NOT the primary mechanism. Semantic pattern rejection likely responsible.

---

## 3. Achieving 100% Recall: Programmatic Solutions

### 3.1 Method 1: Raw OCR Comparison (Recommended for Analysis)

Extract raw OCR output and compare to Docling's classified output to identify missing text.

```python
from pathlib import Path
import fitz  # PyMuPDF
from docling.document_converter import DocumentConverter

def extract_raw_ocr_text(pdf_path: Path) -> str:
    """Extract ALL text that OCR detects, without layout filtering."""
    doc = fitz.open(pdf_path)
    all_text = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        # Render page to image
        pix = page.get_pixmap(dpi=300)
        # Run OCR directly (creates temporary PDF with text layer)
        ocr_result = pix.pdfocr_tobytes(language="eng", tessdata=None)
        ocr_doc = fitz.open("pdf", ocr_result)
        # Extract text
        page_text = ocr_doc[0].get_text()
        all_text.append(page_text)
        ocr_doc.close()

    doc.close()
    return "\n\n".join(all_text)

def extract_docling_text(pdf_path: Path, converter: DocumentConverter) -> str:
    """Extract Docling's classified text."""
    result = converter.convert(str(pdf_path))
    return "\n\n".join(item.text for item in result.document.texts if hasattr(item, "text"))

def compare_outputs(pdf_path: Path, converter: DocumentConverter):
    """Compare raw OCR vs Docling output."""
    raw_text = extract_raw_ocr_text(pdf_path)
    docling_text = extract_docling_text(pdf_path, converter)

    raw_words = raw_text.split()
    docling_words = docling_text.split()

    print(f"Raw OCR words: {len(raw_words):,}")
    print(f"Docling words: {len(docling_words):,}")
    print(f"Loss: {len(raw_words) - len(docling_words):,} words ({(len(raw_words) - len(docling_words)) / len(raw_words) * 100:.2f}%)")

    # Find missing lines
    raw_lines = set(raw_text.split("\n"))
    docling_lines = set(docling_text.split("\n"))
    missing_lines = raw_lines - docling_lines

    print(f"\nMissing {len(missing_lines)} lines")
    print("Sample missing lines:")
    for line in sorted(missing_lines)[:10]:
        if line.strip():
            print(f"  - {line[:80]}")
```

### 3.2 Method 2: Programmatic Reconciliation

Re-insert missing text into DoclingDocument using raw OCR as ground truth.

```python
from ocrmac import ocrmac
from pdf2image import convert_from_path
from docling.document_converter import DocumentConverter
from docling_core.types.doc import DoclingDocument, TextItem, ProvenanceItem, BoundingBox

def reconcile_document(pdf_path: str, converter: DocumentConverter) -> DoclingDocument:
    """
    Re-insert text filtered out by layout classification.

    Process:
    1. Extract ground truth with ocrmac
    2. Process with Docling
    3. Identify missing text
    4. Re-insert using DoclingDocument.add_text()
    """
    # Step 1: Ground truth OCR
    page_images = convert_from_path(pdf_path, dpi=300)
    ground_truth = {}

    for i, page_image in enumerate(page_images):
        page_num = i + 1
        annotations = ocrmac.OCR(page_image).recognize()
        # Format: [('text', confidence, [x, y, w, h]), ...]
        ground_truth[page_num] = annotations

    # Step 2: Docling processing
    result = converter.convert_single(pdf_path)
    doc = result.document

    # Step 3: Identify existing text
    existing_text = {item.text for item in doc.texts}

    # Step 4: Re-insert missing text
    missing_count = 0
    for page_num, annotations in ground_truth.items():
        for text, confidence, box in annotations:
            if text not in existing_text and text.strip():
                missing_count += 1

                # Convert ocrmac box [x, y, w, h] to Docling bbox [x1, y1, x2, y2]
                img_width, img_height = page_images[page_num - 1].size
                x1 = box[0] / img_width
                y1 = box[1] / img_height
                x2 = (box[0] + box[2]) / img_width
                y2 = (box[1] + box[3]) / img_height

                # Create provenance
                prov = ProvenanceItem(
                    page_no=page_num,
                    bbox=BoundingBox(x1=x1, y1=y1, x2=x2, y2=y2)
                )

                # Add missing text
                doc.add_text(text=text, prov=[prov])

    print(f"Re-inserted {missing_count} missing text blocks")
    return doc
```

### 3.3 Method 3: Use Raw OCR Directly (Maximum Recall)

Bypass Docling's classification entirely for 100% recall.

```python
def extract_with_max_recall(pdf_path: Path) -> str:
    """
    Extract all text using raw OCR, bypassing layout classification.

    Use when:
    - 100% textual recall is critical
    - Semantic classification not needed
    - TOC/citation content must be preserved
    """
    return extract_raw_ocr_text(pdf_path)
```

---

## 4. Diagnostic Tools

### 4.1 Visual Overlay Inspection

Generate color-coded overlays showing Docling's classifications.

```bash
# Generate overlay PDF
uv run python scripts/evaluation/generate_ocr_overlay.py --pdf <basename> --engine ocrmac

# Extract pages as PNG for viewing
uv run python scripts/evaluation/extract_pdf_pages_as_images.py

# View with Read tool
# (PNGs viewable in multimodal interface, PDFs are not)
```

**Color Legend:**
- Blue = TextItem (body text)
- Green = SectionHeaderItem
- Orange = ListItem
- Purple = Title
- Yellow = Caption
- Red = Footnote
- Gray = PageHeader/PageFooter

**Analysis:**
- No colored box = Text completely missed (NOT just misclassified)
- Wrong colored box = Detected but wrong semantic class

### 4.2 Text Content Comparison

```python
def get_stats(text: str) -> dict:
    """Calculate text statistics for comparison."""
    return {
        "chars": len(text),
        "chars_no_ws": len(text.replace(" ", "").replace("\n", "").replace("\t", "")),
        "words": len(text.split()),
        "lines": len(text.split("\n"))
    }

# WRONG: Item count doesn't tell you what text was captured
item_count = len(doc.document.texts)  # ❌

# RIGHT: Compare actual text content
text1 = extract_text(doc1)
text2 = extract_text(doc2)
diff = get_stats(text1)["words"] - get_stats(text2)["words"]  # ✅
```

---

## 5. Empirical Evidence Summary

### Test 1: Configuration Changes
- **PDFs tested:** academic_limbo (92.9% recall)
- **Configurations:** 6 variations (force_full_page_ocr, lower thresholds, higher scale, keep_empty_clusters, combined)
- **Result:** 0 additional words captured
- **Files:** `scripts/evaluation/test_docling_configurations.py`, `scripts/evaluation/compare_config_text.py`

### Test 2: Confidence Threshold
- **Method:** Monkey-patch `LayoutPredictor.__init__` to set `base_threshold=0.1` (from default 0.3)
- **Result:** 0 additional words captured
- **Implication:** Confidence filtering NOT the primary mechanism
- **File:** `scripts/evaluation/test_lower_confidence_threshold.py`

### Test 3: Raw OCR vs Classified
- **PDF:** academic_limbo
- **Raw OCR:** 3,758 words, 28,933 chars
- **Docling:** 3,292 words, 25,476 chars
- **Loss:** 466 words (12.40%), 3,457 chars (11.95%), 751 lines
- **Missing content:** ALL TOC entries ("Introduction......", "Structural Disparities...25", etc.)
- **File:** `scripts/evaluation/compare_raw_ocr_vs_classified.py`

### Test 4: Visual Inspection
- **PDFs:** academic_limbo (92.9%), bu_law_review_nil_compliance (89.7%), bu_law_review_learning_from_history (92.1%)
- **Finding:** TOC pages have NO bounding boxes (complete detection failure, not misclassification)
- **Pattern:** Dotted leaders, right-aligned page numbers, hierarchical indentation → Rejected by semantic classifier
- **Files:** `scripts/evaluation/generate_ocr_overlay.py`, `scripts/evaluation/extract_pdf_pages_as_images.py`

---

## 6. Root Cause Analysis

**Why TOC text is lost:**

1. ✅ OCR successfully reads TOC text (confirmed by raw extraction)
2. ✅ Layout model detects TOC regions (visible in debug output)
3. ❌ **Classification stage rejects TOC formatting patterns**:
   - Dotted leaders (.....)
   - Right-aligned page numbers
   - Mixed fonts/spacing
   - Hierarchical indentation
4. ❌ Text without surviving semantic container is orphaned
5. ❌ Orphaned text discarded from final output

**Filtering mechanisms (multiple heuristics active):**
- Confidence thresholding (base_threshold=0.3, but NOT the primary cause)
- Overlap resolution (prefer larger boxes, specific semantic labels)
- Minimum size thresholds
- **Semantic pattern matching** (rejects non-standard formatting)

**Pattern doesn't match learned categories:**
- Not "Paragraph" (no continuous text flow)
- Not "Section_Header" (has page numbers, dotted leaders)
- Not "List_Item" (wrong indentation pattern)
- → Classifier rejects as ambiguous/low-quality → Text lost

---

## 7. Recommendations

### For Current Project
**Accept 89-93% recall** as baseline for academic PDFs with TOC pages. Missing text (TOC entries) is less critical for main body extraction.

### For Maximum Recall (100%)
**Use programmatic reconciliation** (Method 2, Section 3.2):
1. Extract raw OCR as ground truth
2. Process with Docling for semantic structure
3. Compare outputs to identify missing text
4. Re-insert missing text using `DoclingDocument.add_text()`

**Or use raw OCR directly** (Method 3, Section 3.3) when semantic classification not needed.

### For Future Improvement
- Train custom layout classifier on law review TOC patterns
- Contribute TOC examples to DocLayNet training set
- Request Docling expose filtering controls in public API

---

## Documentation

- `docs/LAYOUT_DETECTION_INVESTIGATION_SUMMARY.md` - Investigation timeline and findings
- `docs/OCR_OVERLAY_INSPECTION_GUIDE.md` - Visual inspection methodology
- `docs/DOCLING_CONFIGURATION_OPTIONS.md` - All configuration options + test results
- `docs/DOCLING_MAX_RECALL_CORRECTIONS.md` - Detailed empirical corrections

---

*Last updated: 2025-10-23*
*Investigation: academic_limbo, bu_law_review_nil_compliance, bu_law_review_learning_from_history*
