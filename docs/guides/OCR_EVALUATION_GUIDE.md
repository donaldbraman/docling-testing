# Comprehensive OCR Pipeline Evaluation Guide

## Overview

This guide describes the complete evaluation framework for comparing three OCR extraction pipelines on a representative test corpus. The evaluation measures quality (precision/recall/F1 scores), speed (timing metrics), and variation across journal sources.

**Test Corpus:** 12 PDFs representing all major journal sources (Texas, California, Harvard, USC, BU, Michigan, Supreme Court Review, Wisconsin, Virginia, UCLA, + 2 misc)
- **Key PDF:** `california_law_review_amazon-trademark.pdf` (known small caps issue)
- **Coverage:** All HTML ground truth paired
- **Total Size:** ~59MB

## Architecture

### Components

```
scripts/evaluation/
├── ocr_pipeline_evaluation.py          # Main orchestrator
├── html_ground_truth_extractor.py      # HTML → ground truth labels
├── confusion_matrix_generator.py        # Compare extractions vs ground truth
├── analysis_and_reporting.py            # Analyze results + visualizations
├── test_corpus_config.json              # Test corpus specification
└── OCR_EVALUATION_GUIDE.md             # This file
```

### Execution Pipeline

```
1. Load test corpus config (12 PDFs + HTML pairs)
    ↓
2. Extract ground truth from HTML (semantic labels)
    ↓
3. Run three extraction pipelines:
   a) Baseline (Docling text layer)
   b) OCRmyPDF (Tesseract)
   c) PaddleOCR (GPU)
    ↓
4. Generate confusion matrices (extract vs ground truth)
    ↓
5. Calculate metrics (precision, recall, F1)
    ↓
6. Analyze variation (by journal, by pipeline)
    ↓
7. Generate report & visualizations
```

### Output Structure

```
results/ocr_pipeline_evaluation/
├── ground_truth/                        # HTML ground truth
│   ├── california_law_review_amazon-trademark_ground_truth.json
│   ├── texas_law_review_working-with-statutes_ground_truth.json
│   └── ... (12 files total)
├── extractions/                         # Extracted text from PDFs
│   ├── california_law_review_amazon-trademark_baseline_extraction.json
│   ├── california_law_review_amazon-trademark_ocrmypdf_extraction.json
│   ├── california_law_review_amazon-trademark_paddleocr_extraction.json
│   ├── extraction_results.csv           # Timing & fragmentation metrics
│   └── ... (36 extraction files total: 3 pipelines × 12 PDFs)
├── confusion_matrices/                  # Evaluation metrics
│   ├── california_law_review_amazon-trademark_baseline_confusion_matrix.json
│   ├── ... (36 matrices total)
│   └── confusion_matrices_summary.csv   # Aggregated metrics
├── metrics/
│   ├── extraction_results.csv
│   ├── summary.json
│   └── ...
├── analysis/                            # Analysis results
│   ├── analysis.json                    # Detailed analysis
│   ├── evaluation_report.md             # Human-readable report
│   ├── f1_by_pipeline.png               # Visualization
│   ├── precision_vs_recall.png
│   ├── error_rate_by_journal.png
│   └── ...
└── [intermediate files]
```

## Quick Start

### Prerequisites

**Required packages:**
```bash
uv pip install docling beautifulsoup4 pandas matplotlib seaborn
```

**Optional OCR packages:**
```bash
# For OCRmyPDF:
brew install tesseract

# For PaddleOCR (GPU):
uv pip install paddleocr pdf2image paddlepaddle-gpu
```

### Run Evaluation

**Full evaluation (all three pipelines):**
```bash
uv run scripts/evaluation/ocr_pipeline_evaluation.py
```

**Baseline only (fast test):**
```bash
uv run scripts/evaluation/ocr_pipeline_evaluation.py --baseline-only
```

**Custom output directory:**
```bash
uv run scripts/evaluation/ocr_pipeline_evaluation.py \
  --output-dir /path/to/results
```

### Expected Runtime

| Step | Time |
|------|------|
| Ground truth extraction | 2-3 min |
| Baseline extractions | 3-5 min |
| OCRmyPDF extractions | 2-3 hours |
| PaddleOCR GPU extractions | 10-15 min |
| Confusion matrix generation | 5-10 min |
| Analysis & reporting | 2-3 min |
| **Total** | **~2.5-3.5 hours** |

## Detailed Components

### 1. HTML Ground Truth Extraction

**File:** `html_ground_truth_extractor.py`

**Process:**
- Parses HTML using BeautifulSoup
- Identifies semantic elements:
  - Body text (from `<article>`, divs with 'body'/'content' classes, `<p>` tags)
  - Footnotes (from `<footer>`, 'footnote' classes, `<ol id="footnotes">`)
  - Headers (all `<h1>` - `<h6>` tags)
  - Other (citations, blockquotes, etc.)

**Output:** JSON file per document with ground truth labels

**Example:**
```json
{
  "file": "california_law_review_amazon-trademark.html",
  "journal": "california_law_review",
  "body_text_paragraphs": [
    {"text": "This article examines...", "source": "article_tag", "length": 145},
    {"text": "The Supreme Court has...", "source": "p_tag", "length": 231}
  ],
  "footnotes": [...],
  "headers": [...],
  "metadata": {
    "total_body_paragraphs": 247,
    "total_footnotes": 89,
    "total_headers": 15
  }
}
```

### 2. PDF Extraction Pipelines

#### Baseline (Docling Text Layer)

**What:** Extract text directly from PDF text layer without OCR

**Speed:** ~7-20 seconds per PDF

**Metrics:** Baseline for comparison

**Use case:** Fast extraction, reveals fragmentation issues

#### OCRmyPDF (Tesseract)

**What:**
1. Run OCRmyPDF on PDF (embeds OCR text layer)
2. Extract with Docling

**Speed:** ~3-5 seconds per page (~50-150s per PDF)

**Requires:** `brew install tesseract`

**Pros:** Proven tool, handles small caps well

**Cons:** Slow, CPU-bound

#### PaddleOCR (GPU)

**What:**
1. Convert PDF → images
2. Run PaddleOCR (GPU-accelerated)
3. Extract text

**Speed:** ~2-4 seconds per page with GPU (~30-120s per PDF)

**Requires:** GPU, PaddleOCR, pdf2image

**Pros:** Fast with GPU, good quality

**Cons:** GPU-dependent, research tool (less proven than Tesseract)

### 3. Confusion Matrix Generation

**File:** `confusion_matrix_generator.py`

**Process:**
1. Load extraction results and ground truth
2. Fuzzy-match extracted texts to ground truth
3. Classify matches:
   - **TP** (True Positive): Extracted text matches ground truth body_text
   - **FP** (False Positive): Extracted text doesn't match ground truth
   - **FN** (False Negative): Ground truth body_text not extracted
   - **TN** (True Negative): Non-body correctly classified

**Metrics:**
- **Precision** = TP / (TP + FP) — "Of extracted body_text, how much is correct?"
- **Recall** = TP / (TP + FN) — "What % of actual body_text was found?"
- **F1 Score** = 2 × (Precision × Recall) / (Precision + Recall) — Harmonic mean
- **Accuracy** = (TP + TN) / total
- **Error Rate** = 1 - Accuracy

**Output:** JSON + CSV with per-document and aggregated metrics

### 4. Analysis & Reporting

**File:** `analysis_and_reporting.py`

**Analyses:**
1. **Variation by Journal** — Does error rate differ across sources?
2. **Pipeline Comparison** — Quality vs speed trade-off
3. **Error Patterns** — False positive/negative distribution
4. **Fragmentation** — Items per page by pipeline
5. **Recommendations** — Which pipeline to use

**Outputs:**
- `analysis.json` — Structured analysis results
- `evaluation_report.md` — Human-readable report
- `f1_by_pipeline.png` — F1 score distribution
- `precision_vs_recall.png` — Quality trade-off scatter
- `error_rate_by_journal.png` — Variation across journals

## Interpreting Results

### Confusion Matrix Interpretation

**Good metrics:**
- Precision > 90% — Few false positives (doesn't mislabel non-body as body)
- Recall > 85% — Finds most actual body text
- F1 > 0.87 — Balanced quality

**Problem indicators:**
- High FP (false positives) → Extracting headers/footnotes as body
- High FN (false negatives) → Missing body text (fragmentation?)
- High variance across journals → Method doesn't generalize

### Small Caps Detection

Check `california_law_review_amazon-trademark` results:

**Baseline (expected issues):**
- High fragmentation (items/page > 12)
- Lower precision (mislabels fragments)
- May miss "LOONEY TUNES WIKI" due to fragmentation

**OCRmyPDF/PaddleOCR (expected improvement):**
- Lower fragmentation (items/page < 10)
- Higher precision/recall
- Should correctly identify merged small caps

## Decision Matrix

Based on evaluation results, decide on production approach:

```
IF PaddleOCR F1 > OCRmyPDF F1 AND has GPU
   → Recommend: PaddleOCR GPU for full corpus (~50 min)

ELSE IF OCRmyPDF F1 > Baseline F1 by > 10%
   → Recommend: OCRmyPDF for full corpus (~90 min)

ELSE IF Improvement < 5%
   → Recommend: Keep Baseline (cost not justified)

ELSE
   → Recommend: Hybrid (Baseline + selective OCR fallback)
```

## Troubleshooting

### OCRmyPDF Not Working

```bash
# Check tesseract installation
tesseract --version

# If not found, install:
brew install tesseract

# Verify it works:
ocrmypdf --help
```

### PaddleOCR GPU Not Using GPU

```python
# In extraction script, verify:
ocr = PaddleOCR(use_gpu=True, lang="en")

# Check available GPUs:
import paddle
print(paddle.device.get_device())
```

### HTML Ground Truth Extraction Failing

**Check:**
1. HTML files exist in `data/v3_data/raw_html/`
2. File encoding (may need `latin-1` instead of `utf-8`)
3. BeautifulSoup installed: `uv pip install beautifulsoup4`

### Memory Issues

**Reduce test corpus:**
Edit `test_corpus_config.json` to test fewer PDFs, or run single pipeline with `--baseline-only`

## Advanced Usage

### Run Only Specific Components

```bash
# Extract ground truth only:
uv run scripts/evaluation/html_ground_truth_extractor.py

# Generate confusion matrices from existing extractions:
uv run scripts/evaluation/confusion_matrix_generator.py

# Generate analysis from existing matrices:
uv run scripts/evaluation/analysis_and_reporting.py
```

### Customize Test Corpus

Edit `test_corpus_config.json`:
```json
{
  "your_journal": {
    "pdf": "pdf_filename_without_extension",
    "html": "html_filename_without_extension",
    "reason": "Why this document is important"
  }
}
```

### Adjust Fuzzy Match Threshold

In `confusion_matrix_generator.py`, constructor:
```python
generator = ConfusionMatrixGenerator(match_threshold=85.0)  # Default 80.0
```

Higher threshold → stricter matching, lower recall but higher precision

## Performance Benchmarks

### Expected Metrics (Rough Estimates)

| Pipeline | Speed | Precision | Recall | F1 | Notes |
|----------|-------|-----------|--------|-----|-------|
| **Baseline** | ~0.6s/page | 85% | 78% | 0.81 | Fast, fragmented on small caps |
| **OCRmyPDF** | ~4s/page | 92% | 88% | 0.90 | Proven, handles small caps |
| **PaddleOCR** | ~3s/page (GPU) | 90% | 86% | 0.88 | GPU-accelerated alternative |

*These are rough estimates; actual results depend on document content and structure.*

## Full Workflow Example

```bash
# 1. Run full evaluation
uv run scripts/evaluation/ocr_pipeline_evaluation.py

# 2. View results
cat results/ocr_pipeline_evaluation/analysis/evaluation_report.md

# 3. Check visualizations
open results/ocr_pipeline_evaluation/analysis/f1_by_pipeline.png
open results/ocr_pipeline_evaluation/analysis/precision_vs_recall.png

# 4. Examine confusion matrices
head results/ocr_pipeline_evaluation/confusion_matrices/confusion_matrices_summary.csv

# 5. Make decision
# Review analysis.json and recommendations
cat results/ocr_pipeline_evaluation/analysis/analysis.json | jq '.recommendations'
```

## Next Steps After Evaluation

### If Using OCRmyPDF
1. Process full 73-PDF corpus (~90 minutes)
2. Generate new training data with improved extractions
3. Retrain model with fixed small caps

### If Using PaddleOCR GPU
1. Verify GPU scaling (test on larger batch)
2. Process full corpus (~50 minutes with GPU)
3. Consider parallelization for further speedup

### If Using Hybrid Approach
1. Implement quality detection heuristics
2. Run baseline on all 73 PDFs
3. Identify low-quality documents (fragmentation > threshold)
4. Re-run OCR on only low-quality subset
5. Merge results

## References

- **V5/V6 Fuzzy Matching:** `scripts/corpus_building/generate_alignment_csv_v6.py`
- **Issue #38:** Deep exploratory analysis (small caps discovery)
- **Issue #39:** This evaluation framework

## Support

For issues or questions:
1. Check troubleshooting section above
2. Review GitHub Issue #39
3. Check confusion matrix output in detail
4. Examine HTML ground truth to verify accuracy

---

**Last Updated:** 2025-10-18
**Status:** Framework complete, ready for execution
