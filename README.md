# Docling Testing

Testing Docling PDF extraction for law review articles with optimized settings.

## Purpose

Evaluate Docling as a potential first-pass extractor for the cite-assist pipeline, comparing against:
- Existing 12-factor-agents spatial detection
- Gemini Flash extraction
- MinerU (if GPU available)

## Key Questions

1. **Layout Detection**: Can Docling identify different document parts (body text, footnotes, headers)?
2. **Image Scaling**: Does higher DPI (2x, 3x) improve detection accuracy?
3. **Hyphenation**: How many line-break hyphenation artifacts remain?
4. **Speed vs Quality**: Optimal settings for M1 Pro?
5. **Footnote Handling**: Can we programmatically filter footnotes using layout labels?

## Setup

```bash
# Install dependencies
uv sync

# Run scaling test (recommended)
uv run python test_scaling.py

# Or basic test
uv run python test_docling.py
```

## Hardware

**System**: M1 Pro MacBook with 32GB RAM
**Accelerator**: MPS (Metal Performance Shaders)
**OCR**: ocrmac (native Mac OCR)

## Configuration

Using **Heron layout model** with optimized settings:

```python
pipeline = PdfPipelineOptions(
    layout_options=LayoutOptions(),  # Heron model (78% mAP)
    generate_parsed_pages=True,      # Get bounding boxes + labels
    generate_page_images=True,       # Visualize detections
    images_scale=2.0,                # Higher DPI for small fonts
    do_table_structure=True,         # Accurate table detection
    do_ocr=True,                     # For scanned docs
)
```

## Test Corpus

Law review articles from 12-factor-agents:
- `Nedrud_1964.pdf` - Classic older article (1.9 MB)
- `Jackson_2014.pdf` - Recent academic paper (6.6 MB) - **SCALING TEST**
- `Green_Roiphe_2020.pdf` - Modern law review (3.0 MB)

## Scaling Test

Testing Jackson_2014.pdf with three image scales:
- **1.0x** - Default resolution (baseline)
- **2.0x** - 2x DPI (better for small fonts/footnotes)
- **3.0x** - 3x DPI (maximum quality, slower)

Comparing:
- Processing time
- Footnote detection accuracy (bounding boxes)
- Text quality / hyphenation artifacts
- Memory usage

## Initial Findings

**Speed (M1 Pro, default settings):**
- Average: ~2 minutes per document
- Compare: Spatial detector (9s), Gemini Flash (5-10s)

**Quality Issues:**
- ✅ Full text extraction
- ✅ Multi-column layout handling
- ❌ 47 hyphenation artifacts (need Flash cleanup)
- ❓ Footnote detection pending (testing with parsed pages)

## Results

Results saved to:
- `results/docling/` - Basic markdown outputs
- `results/scaling_test/` - Scaling comparison outputs
- `results/layout_analysis_v2/` - Layout detection details

## Cost Analysis

- **Docling**: $0 per document (local compute)
- **Optional Flash cleanup**: $0.02 per document (fix hyphenation)
- **Total**: ~$0.02 per document vs $0.065 for pure Gemini Flash

**Savings: ~69%** (same as spatial + cleanup approach)

## Next Steps

1. ⏳ **Complete scaling test** (running now)
2. **Analyze layout detection quality**
   - Can we filter footnotes programmatically?
   - Do higher scales improve detection?
3. **If promising:**
   - Test on larger corpus (20-30 articles)
   - Create comparison script (Docling vs Gemini vs Spatial)
   - Integrate as fallback in 12-factor-agents

## Context

Gemini 3.0 is coming soon with improved quality. This testing helps us:
- Understand current baseline
- Prepare for hybrid approach (local + API)
- Have fallback if Gemini 3.0 doesn't meet expectations
- Evaluate true cost of local vs cloud extraction
