# V3 Corpus Status Report

**Updated:** 2025-10-17 (Evening)
**Pipeline:** v3 (Pure Positive Inclusion)

## Overview

- **Total HTML-PDF Pairs:** 80 (doubled from 40!)
- **Validated Journals:** 3 (21 articles, 26.2%)
- **Journals Needing Validation:** 8 (59 articles, 73.8%)

## Journal Breakdown

### ✅ VALIDATED (HTML extraction tested & verified)

| Journal | Articles | Validation Status | Sample Size |
|---------|----------|-------------------|-------------|
| **BU Law Review** | 8 | ✅ Perfect footnote matching | 614 paras |
| **Michigan Law Review** | 5 | ✅ Perfect footnote matching | 1,888 paras |
| **Supreme Court Review** | 8 | ✅ Perfect footnote matching | 805 paras |
| **TOTAL VALIDATED** | **21** | **All patterns working** | **3,307 paras** |

### ⚠️  NEEDS VALIDATION (≥5 articles, ready for testing)

| Journal | Articles | Status |
|---------|----------|--------|
| **California Law Review** | 11 | Ready - uses generic pattern |
| **Harvard Law Review** | 6 | Ready - uses generic pattern |
| **Texas Law Review** | 11 | Ready - uses generic pattern |
| **USC Law Review** | 10 | Ready - uses generic pattern |
| **Other/Westlaw** | 17 | Needs investigation |

### ⚠️  BELOW THRESHOLD (<5 articles)

| Journal | Articles | Status |
|---------|----------|--------|
| University of Chicago | 2 | Below threshold, may skip |
| Virginia Law Review | 1 | Below threshold, may skip |
| Wisconsin Law Review | 1 | Below threshold, may skip |

## Source Breakdown

**Original sources:**
- Downloads folder: 27 pairs
- data/raw_html + raw_pdf: 13 pairs

**Repository sources:**
- data/high_quality_law_reviews: 30 pairs
- data/paired_corpus_review: 10 pairs

## Quality Control

### Pure Positive Inclusion Results

After removing length/word count filters:
- ✅ Recovered 327 missing footnotes (+18.4%)
- ✅ All "Id." citations now included (3-5 chars)
- ✅ All statute refs now included (14-19 chars)
- ✅ Perfect 1:1 footnote matching on all validated journals

## Next Steps (Priority Order)

1. **Validate Harvard Law Review** (6 articles)
   - Uses generic superscript pattern
   - Should be quick - pattern already coded

2. **Validate California Law Review** (11 articles)
   - Uses generic superscript pattern
   - Largest untested journal

3. **Validate Texas Law Review** (11 articles)
   - Uses generic superscript pattern
   - Largest untested journal

4. **Validate USC Law Review** (10 articles)
   - Uses generic superscript pattern
   - Good sample size

5. **Investigate "Other" category** (17 articles)
   - Identify actual journals
   - Determine extraction patterns
   - May include Columbia, Westlaw sources, etc.

6. **Run full extraction pipeline**
   - Extract all 80 HTML files → processed_html/
   - Run Docling on all 80 PDFs → docling_extraction/
   - Match and relabel → relabeled_extraction/
   - Build final training corpus

## Current State

```
data/v3_data/
├── raw_html/              80 HTML files (ground truth) ✅
├── raw_pdf/               80 PDF files (for Docling) ✅
├── processed_html/        0 files (awaiting extraction)
├── docling_extraction/    0 files (awaiting Docling run)
├── relabeled_extraction/  0 files (awaiting matching)
├── INVENTORY.json         (updated) ✅
├── README.md              (pipeline docs) ✅
└── STATUS_REPORT.md       (this file) ✅
```

---

**Current Progress:** 26.2% validated (21/80 pairs)
**Next Task:** Continue HTML extraction validation for remaining journals
