# Data Collection Guide

**Code Version:** 0.1.0
**Last Updated:** 2025-10-15

## Purpose

Guide to collecting PDFs and building training corpus for DoclingBERT models.

## Quick Start

```bash
# 1. Scrape law review PDFs
python scrape_law_reviews.py

# 2. Extract labels from PDFs
python extract_all_docling_labels.py

# 3. Build clean corpus
python build_clean_corpus.py

# 4. Verify corpus
python build_clean_corpus.py --analyze
```

## Current Corpus

**Size:** 37,888 paragraphs across 7 semantic classes

**Distribution:**
- footnote: 31,809 samples (84.0%)
- body_text: 5,895 samples (15.6%)
- caption: 184 samples (0.5%)
- heading, page_header, page_footer, cover: Limited samples

**Sources:**
1. Semantic PDF tags (31,809 samples) - Highest quality
2. HTML-PDF matching (1,733 samples)
3. Cover page patterns (2,340 samples)

**Imbalance ratio:** 5.4:1 (footnote:body_text)

## Data Collection Workflow

### Step 1: Scrape PDFs

```bash
# Scrape from multiple law reviews
python scrape_law_reviews.py

# Target: 250 PDFs from 25 journals
# Output: data/raw_pdf/*.pdf
```

**Available sources:**
- UCLA Law Review (~150 more PDFs)
- Georgetown Law (~200 PDFs)
- Texas Law (~180 PDFs)
- Annual Reviews (~300 PDFs)

**Total available:** ~800+ PDFs (~26,000 estimated body_text samples)

### Step 2: Extract Labels

```bash
# Extract Docling labels from PDFs
python extract_all_docling_labels.py

# Output: data/full_docling_corpus.csv
```

**Extraction methods:**
1. **Semantic PDF tags** (preferred)
   - High quality, directly from PDF metadata
   - Accurate paragraph-level classification

2. **HTML-PDF matching**
   - Cross-reference HTML source with PDF
   - Good for body_text verification

3. **Cover page detection**
   - HeinOnline, JSTOR, Annual Reviews patterns
   - Brittle but effective for known formats

### Step 3: Build Clean Corpus

```bash
# Merge sources and clean
python build_clean_corpus.py

# Output: data/clean_7class_corpus.csv
```

**Cleaning steps:**
1. Deduplicate paragraphs
2. Remove empty/whitespace-only texts
3. Verify label consistency
4. Balance class distribution (via class weights, not sampling)

### Step 4: Verify Quality

```bash
# Analyze corpus statistics
python build_clean_corpus.py --analyze

# Expected output:
# - Class distribution
# - Sample counts per source
# - Imbalance ratios
```

## Data Quality Checklist

- [ ] No duplicate paragraphs
- [ ] All texts have non-empty content
- [ ] Label distribution known (calculate imbalance ratio)
- [ ] Source tracking enabled (for provenance)
- [ ] Minimum 1,000 samples per target class (body_text, footnote)

## Expanding Corpus

**To add 2x body_text samples (~6,000):**

```bash
# 1. Scrape ~180 more PDFs
python scrape_law_reviews.py --journals ucla,georgetown --count 180

# 2. Extract labels
python extract_all_docling_labels.py

# 3. Rebuild corpus
python build_clean_corpus.py

# 4. Retrain
python train_multiclass_classifier.py
```

**Expected improvements with 2x data:**
- Imbalance ratio: 5.4:1 → 2.6:1
- Expected recall: 83% → 87-90%
- FP:FN ratio: 0.85:1 → 1.5-2.0:1

**To add 3x body_text samples (~12,000):**
- Need: ~360 more PDFs
- Time: 4-8 hours (scraping + extraction)
- Expected recall: 90-93%

## Troubleshooting

### Scraper Issues

See [Troubleshooting](troubleshooting.md) - Scraper section

### Low Sample Counts

**Problem:** Only 184 caption samples

**Solutions:**
1. **Accept limitation** - Use class weights to handle imbalance
2. **Collect more** - Focus on PDFs with figures/tables
3. **Synthetic data** - Generate captions from figure descriptions (future)

## Related Guides

- [Model Training](model-training.md) - Using collected corpus
- [Troubleshooting](troubleshooting.md) - Scraper issues

---

**Last Updated:** 2025-10-15
