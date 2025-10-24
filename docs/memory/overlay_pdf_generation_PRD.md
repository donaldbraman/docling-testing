# PRD: Overlay PDF Generation for OCR Pipeline Evaluation

## Overview
Generate overlay PDFs that visualize classification accuracy by displaying colored bounding boxes around text regions, comparing Docling's original classifications against ground truth labels from HTML sources.

## Goals
1. Create visual tools to evaluate OCR pipeline accuracy
2. Enable side-by-side comparison of uncorrected vs corrected classifications
3. Support quantitative analysis of classification errors
4. Provide accurate line-level matching to HTML ground truth

## Components

### 1. Uncorrected Overlay PDF
**Purpose:** Show Docling's original paragraph-level classifications

**Input:**
- Original PDF
- Docling extraction JSON (paragraph-level items with bboxes)

**Output:**
- PDF with colored boxes showing Docling's labels:
  - Blue = TEXT class (body text)
  - Red = FOOTNOTE class
  - Green = SECTION_HEADER
  - Gray = PAGE_HEADER / PAGE_FOOTER

**Implementation:**
- Use Docling's paragraph-level bboxes directly
- Apply coordinate transformation (BOTTOMLEFT @ ~200 DPI → TOPLEFT @ 72 DPI)
- Semi-transparent fills (40% opacity) for readability

### 2. Corrected Overlay PDF
**Purpose:** Show ground truth labels using line-level fuzzy matching

**Input:**
- Original PDF
- HTML ground truth (body_html and footnote_html lists)

**Output:**
- PDF with colored boxes showing corrected labels:
  - Blue = body-text (from HTML)
  - Red = footnote-text (from HTML)
  - Merged boxes around adjacent lines with same label

**Implementation:**
- Extract line-level text and bboxes from PDF using PyMuPDF
- Fuzzy match each line to HTML ground truth
- Group adjacent lines with same label (spatial adjacency < 5px)
- Draw merged bounding boxes for each group

## Fuzzy Matching Requirements

### Basic Matching (Current)
1. **Text Similarity:** Use RapidFuzz or difflib to compute similarity scores (0.0-1.0)
2. **Threshold:** Only accept matches above 0.75 similarity
3. **Best Match:** For each line, find the best match across all HTML segments
4. **Label Assignment:** Assign "body-text" or "footnote-text" based on which HTML list matched

### Locality-Aware Matching (Phase 2) ⚠️ **REQUIRED**

**Problem:** Current approach allows same HTML segment to match multiple non-adjacent PDF lines, causing overlapping boxes.

**Solution:** Implement locality preference to ensure natural forward flow through HTML.

**Algorithm:**
1. **Initialization:**
   - Track `current_body_position` (index in body_html list)
   - Track `current_footnote_position` (index in footnote_html list)
   - Start both at 0

2. **For each PDF line (top to bottom):**
   - Find ALL matches in body_html with similarity > threshold
   - Find ALL matches in footnote_html with similarity > threshold

3. **Apply proximity weighting:**
   - For each match, calculate proximity score:
     - `distance = abs(match_index - current_position)`
     - `proximity_bonus = 0.1 / (1.0 + distance * 0.1)`  # Max 0.1, not 1.0
   - Combine similarity + proximity:
     - `final_score = similarity_score + proximity_bonus`
   - **Key tuning**: Proximity bonus scaled to 0-0.1 range so similarity (0.75-1.0) dominates
     - Prevents bias toward recently-used HTML list
     - Ensures high-similarity matches win regardless of position

4. **Select best match:**
   - Choose match with highest final_score
   - Update current_position to match_index + 1

5. **Result:**
   - Natural forward flow through HTML that mirrors PDF reading order
   - Each HTML segment typically used once
   - Allows backward jumps when similarity score clearly dominates

**Tie-Breaking Behavior:**
- High similarity dominates: 0.95 match at distance 50 beats 0.80 match at distance 1
- Similar scores prefer proximity: 0.80 at distance 1 beats 0.78 at distance 50

**Benefits:**
- Eliminates overlapping boxes (each HTML used once)
- Maintains accuracy (still uses similarity as primary criterion)
- Creates coherent visualization of HTML-to-PDF mapping

## Coordinate Transformation

**Problem:** Docling uses BOTTOMLEFT origin @ ~200 DPI, PyMuPDF uses TOPLEFT @ 72 DPI

**Solution:** Empirically-derived transformation from control points:

```python
# Constants (from page 5 calibration)
DOCLING_MAX_Y = 2205.68
X_SCALE = 0.320937
X_OFFSET = 0.203006
Y_SCALE = 0.322262
Y_OFFSET = 84.225026

# Transform
pdf_x = docling_x * X_SCALE + X_OFFSET
pdf_y = (DOCLING_MAX_Y - docling_y) * Y_SCALE + Y_OFFSET
```

**Accuracy:** Sub-pixel (<1px) error verified on page headers and body text

## Output Format

**File naming:**
- Uncorrected: `{pdf_name}_baseline_uncorrected.pdf`
- Corrected: `{pdf_name}_baseline_corrected.pdf`

**Location:** `results/overlay_pdfs/`

**Legend:** Included on first page showing color mapping

## Success Criteria

✅ **Completed:**
- [x] Accurate coordinate transformation (<1px error)
- [x] Line-level text extraction from PDF
- [x] Fuzzy matching to HTML ground truth
- [x] Adjacent line grouping with spatial checks
- [x] Semi-transparent overlays with proper colors
- [x] Uncorrected PDF shows Docling classifications

✅ **Phase 2 Complete:**
- [x] Locality-aware matching to prevent overlaps
- [x] Validation that each HTML segment used at most once
- [x] Fallback to Docling labels for unmatched lines (complete coverage)
- [x] Tuned proximity weight (0-0.1) to prevent bias toward recent list

## Implementation Status

**Current:** Phase 2 Complete ✅
- Locality-aware fuzzy matching implemented
- Proximity bonus properly scaled (max 0.1) so similarity dominates
- Fallback to Docling classifications ensures all text classified
- Line-level extraction and spatial grouping working correctly
- No overlapping boxes verified
- Complete text coverage across all pages

## Files

**Core:**
- `scripts/evaluation/generate_overlay_pdfs.py` - Main overlay generator
- `scripts/evaluation/fuzzy_matcher.py` - Matching logic (needs locality update)
- `scripts/evaluation/parse_extraction.py` - Docling JSON parser
- `scripts/evaluation/prepare_matching_data.py` - HTML ground truth loader

**Output:**
- `results/overlay_pdfs/*.pdf` - Generated overlay PDFs

---

**Last Updated:** 2025-10-20
**Status:** Phase 2 Complete ✅
