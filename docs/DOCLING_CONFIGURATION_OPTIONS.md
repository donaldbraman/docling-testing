# Docling Configuration Options

## PdfPipelineOptions Parameters

### Layout Detection (Most Relevant for TOC Issues)

**layout_options** (dict):
- `create_orphan_clusters`: bool = True
  - Create clusters for text not assigned to other structures
- `keep_empty_clusters`: bool = False
  - Keep clusters even if they have no content
- `model_spec`: Layout detection model configuration
  - Default: 'docling_layout_heron' from ds4sd/docling-layout-heron
- `skip_cell_assignment`: bool = False
  - Skip assigning cells in tables

### OCR Options (Affects Text Detection)

**ocr_options** (dict):
- `lang`: list = []
  - OCR language codes (empty = auto-detect)
- `force_full_page_ocr`: bool = False
  - **KEY**: Force OCR on entire page instead of just bitmap regions
  - **May help**: Capture text missed by layout detection
- `bitmap_area_threshold`: float = 0.05
  - **KEY**: Only OCR regions > 5% of page area
  - **May help**: Lower threshold to capture smaller text regions (TOC entries, small fonts)

**do_ocr**: bool = True
- Enable/disable OCR entirely

**force_backend_text**: bool = False
- Use embedded PDF text instead of OCR (not useful for image-only PDFs)

### Image Processing

**images_scale**: float = 1.0
- Scale factor for image processing
- Higher values = more detail but slower
- **May help**: Increase to 1.5 or 2.0 for better small text detection

### Accelerator Options

**accelerator_options** (dict):
- `num_threads`: int = 4
- `device`: str = 'auto' (cpu/cuda/mps)
- `cuda_use_flash_attention2`: bool = False

### Table Processing

**do_table_structure**: bool = True
**table_structure_options** (dict):
- `do_cell_matching`: bool = True
- `mode`: str = 'accurate'

### Timeouts

**document_timeout**: int | None = None
- Maximum processing time per document

## Configurations to Test for TOC Detection

### Config 1: Force Full Page OCR
```python
pipeline_options.ocr_options.force_full_page_ocr = True
```
**Hypothesis**: Layout detection misses TOC; full-page OCR might capture it

### Config 2: Lower Bitmap Threshold
```python
pipeline_options.ocr_options.bitmap_area_threshold = 0.01  # 1% instead of 5%
```
**Hypothesis**: TOC entries too small, below 5% threshold

### Config 3: Increase Image Scale
```python
pipeline_options.images_scale = 2.0
```
**Hypothesis**: Higher resolution helps detect small fonts

### Config 4: Keep Empty Clusters
```python
pipeline_options.layout_options.keep_empty_clusters = True
```
**Hypothesis**: TOC clusters created but discarded as "empty"

### Config 5: Combined Aggressive
```python
pipeline_options.ocr_options.force_full_page_ocr = True
pipeline_options.ocr_options.bitmap_area_threshold = 0.01
pipeline_options.images_scale = 2.0
pipeline_options.layout_options.keep_empty_clusters = True
```
**Hypothesis**: Multiple issues; combined approach needed

## Current Configuration

**Default (as used in all evaluations so far)**:
```python
pipeline_options = PdfPipelineOptions()
pipeline_options.do_ocr = True
pipeline_options.ocr_options = OcrMacOptions()  # or other engine
```

All other options use defaults shown above.

## Test Results (academic_limbo, 92.9% recall)

Tested 6 configurations on academic_limbo PDF with known TOC detection failures:

| Configuration | Items Extracted | Difference |
|---|---|---|
| Default (baseline) | 94 | - |
| Force full page OCR | 94 | 0 |
| Lower bitmap threshold (0.01) | 94 | 0 |
| Higher image scale (2.0x) | 94 | 0 |
| **Keep empty clusters** | **95** | **+1** |
| **Combined aggressive** | **95** | **+1** |

### Key Findings

1. **Item count misleading**: +1 item does NOT mean +1 meaningful text unit
2. **Actual text comparison** (default vs keep_empty_clusters):
   - Character difference: +2 (+0.01%)
   - Character difference (no whitespace): **0 (+0.00%)**
   - Word difference: **0 (+0.00%)**
   - Line difference: +2 (blank lines only)
3. **Zero content recovered**: The +1 item was an empty cluster with no text
4. **Configuration has no impact**: All parameter changes failed to capture TOC text

### Methodology: Proper Configuration Comparison

**Wrong approach:** Count items
```python
len(doc.document.texts)  # ❌ Items can be empty or merged
```

**Right approach:** Compare actual text content
```python
# Extract all text
text = "\n\n".join(item.text for item in doc.document.texts)

# Compare character/word counts
chars = len(text)
words = len(text.split())
chars_no_ws = len(text.replace(" ", "").replace("\n", ""))

# Generate diff to see what changed
```

See `scripts/evaluation/compare_config_text.py` for full implementation.

### Conclusion

**Configuration tweaks cannot recover missing TOC text.** The layout detection model fails to recognize TOC formatting patterns (dotted leaders, page numbers, indented structure). Even "successful" configuration changes (keep_empty_clusters) added **0 words** of actual content.

**Recommendation**: Accept 89-93% recall as baseline for PDFs with complex TOC pages when using default Docling layout model.
