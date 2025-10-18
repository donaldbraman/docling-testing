# Corpus Cleanup Summary

**Date:** 2025-10-17

## Overview

Cleaned the HTML-PDF corpus to remove unusable pairs, resulting in a clean set of 85 perfectly matched HTML-PDF pairs suitable for training data generation.

## What Was Removed

### 1. Abstract-Only Pages (388 HTML files)

**Why removed:** These HTML files contained only article abstracts, metadata, and links to PDFs - not full article text.

**Evidence:** Average Jaccard similarity of 23.22% with their PDFs (vs 76.96% for full-text files).

**Location:** `data/archived_abstract_only/`

**Sources affected:**
- Georgetown Law Journal (all abstract-only)
- Duke Law Journal (all abstract-only)
- Northwestern Law Review (mostly abstract-only)
- Florida Law Review (all abstract-only)
- Penn Law Review (abstract pages with metadata)
- Cornell Law Review (all abstract-only)
- GWU Law Review (all abstract-only)

### 2. Unpaired Files (37 HTML + 10 PDF)

**Why removed:** No matching HTML-PDF pair available.

**Breakdown:**
- 37 law review HTML files without PDFs (mostly California, Harvard)
- 10 arXiv PDF files without HTML

**Location:** `data/archived_unpaired/` (combined HTML and PDF in single folder for easy review)

## Final Clean Corpus

### Summary Statistics

```
Total matched pairs:  85
  - arXiv:            38 pairs
  - Law reviews:      47 pairs
```

### Law Review Sources (47 pairs)

**Full-text HTML sources:**
- **California Law Review**: 11 pairs (from 18 HTML files)
- **Texas Law Review**: 26 pairs
- **USC Law Review**: 5 pairs (from 11 HTML files)
- **Harvard Law Review**: 2 pairs (from 5 HTML files)
- **Boston University Law Review**: 2 pairs
- **Columbia Law Review**: 1 pair

### arXiv Papers (38 pairs)

All arXiv papers are full-text HTML with matching PDFs:
- Computer Science (AI, ML, CL)
- Physics
- Mathematics
- Economics

### Quality Validation

**Average Jaccard similarity:**
- Law reviews: ~77% (high-quality matches)
- arXiv: ~50% (lower due to math/equations, but still valid)

## Files Created During Cleanup

### Analysis Scripts

1. **`scripts/analysis/categorize_html_types.py`**
   - Categorizes HTML files as full-text vs abstract-only
   - Word count analysis, PDF link detection, confidence scoring

2. **`scripts/corpus_building/remove_abstract_only_pairs.py`**
   - Archives abstract-only HTML-PDF pairs
   - Preserves full-text pairs only

3. **`scripts/corpus_building/remove_unpaired_html.py`**
   - Archives unpaired HTML and PDF files
   - Ensures all remaining files have matching pairs

### Results Files

1. **`data/html_categorization_results.csv`**
   - Full categorization of 472 HTML files
   - Columns: basename, category, word_count, has_pdf_download_link, confidence

2. **`data/law_review_quality_scores.csv`**
   - Jaccard similarity scores for all 206 law review pairs
   - Sorted by quality score (lowest to highest)

3. **`data/law_review_quality_scores.json`**
   - Detailed results with histogram of quality distribution

### Archive Reports

1. **`data/archived_abstract_only/CLEANUP_REPORT.md`**
   - Summary of 388 abstract-only HTML files archived
   - 159 matching PDFs archived (229 were already missing)

2. **`data/archived_unpaired/CLEANUP_REPORT.md`**
   - Summary of 37 unpaired HTML and 10 unpaired PDF files
   - All archived together in single directory for easy review

## Impact on Training Corpus

### Before Cleanup

- 510 HTML files (mixture of full-text and abstract-only)
- 254 PDF files (many missing)
- ~206 apparent pairs (but most unusable due to content mismatch)

### After Cleanup

- 85 HTML files (all full-text)
- 85 PDF files (perfectly matched)
- **85 usable pairs for HTML-PDF matching**

### Expected Training Data

From 85 high-quality HTML-PDF pairs:
- Estimated paragraphs per pair: ~200-300
- Total estimated paragraphs: **17,000-25,000 labeled samples**
- 7 semantic classes with HTML ground truth labels

This is sufficient for initial DoclingBERT v3 training with balanced sampling.

## Next Steps

1. **Phase 1: PDF Selection** (COMPLETE)
   - ✅ Validated HTML-PDF pairs (85 pairs confirmed)
   - ✅ Removed unusable pairs
   - ✅ Created clean corpus

2. **Phase 2: Complete Docling Extraction**
   - Extract features from all 85 PDF files
   - Capture full paragraph content and metadata

3. **Phase 3: HTML Ground Truth Labeling**
   - Match paragraphs to HTML source
   - Assign semantic labels based on HTML structure

4. **Phase 4: Master Corpus Assembly**
   - Combine features + labels
   - Create complete dataset for flexible sampling

5. **Phase 5-9: Training, Evaluation, Deployment**
   - See `docs/issues/ISSUE_CORPUS_V3_REBUILD.md` for full plan

## Restoration Instructions

If you need to restore archived files:

### Abstract-Only Pages
```bash
# Restore HTML
cp data/archived_abstract_only/html/*.html data/raw_html/

# Restore PDFs (if needed)
cp data/archived_abstract_only/pdf/*.pdf data/raw_pdf/
```

### Unpaired Files
```bash
# Restore from combined archive
cp data/archived_unpaired/*.html data/raw_html/
cp data/archived_unpaired/*.pdf data/raw_pdf/
```

---

*Generated: 2025-10-17*
*Corpus v3 rebuild preparation*
