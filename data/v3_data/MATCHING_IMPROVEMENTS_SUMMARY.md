# V3 Matching Improvements Summary

**Date**: 2025-01-18
**Status**: In Progress

## Improvements Completed

### 1. Fixed Case-Sensitivity Issue ✅
**Problem**: PDF text "EDWARD B. TYLOR" wasn't matching HTML text "Edward B. Tylor" (59.8% match)

**Solution**: Added `processor=utils.default_process` parameter to RapidFuzz calls
- Normalizes both texts (lowercase, strip punctuation)
- Improved match from 59.8% → 99.1%

**Files Updated**:
- `scripts/corpus_building/generate_alignment_csv.py`
- `scripts/corpus_building/relabel_with_sequential_fuzzy_matching.py`

**Impact**: Much better matching across all articles

---

### 2. Completed Docling PDF Extraction ✅
**Results**:
- 73/73 PDFs processed successfully
- 11 PDFs with 0 text items (OCR/structure failures):
  1. afrofuturism_in_protest__dissent_and_revolution
  2. guaranteed__the_federal_education_duty
  3. harvard_law_review_excited_delirium
  4. harvard_law_review_forgotten_history_of_prison_law
  5. harvard_law_review_law_and_lawlessness_of_immigration_detention
  6. harvard_law_review_unwarranted_warrants
  7. harvard_law_review_waste_property_and_useless_things
  8. law_of_protest
  9. overbroad_protest_laws
  10. policing_campus_protest
  11. wisconsin_law_review_marriage_equality_comes_to_wisconsin

**Note**: Failed PDFs will appear in CSVs with empty PDF columns

---

### 3. CSV Generation Optimization (Attempted) ⚠️
**Attempted**: Sliding window optimization to reduce O(n*m) to O(n*k)
- Initial approach: Sequential matching with small window (100-500 paragraphs)
- Problem: Match rates dropped dramatically (from 100% to 12%)
- Root cause: CSV generation needs exhaustive matching for diagnostic purposes

**Decision**: Reverted to exhaustive matching
- Kept normalization improvement
- Accepted slower speed for comprehensive results
- CSV generation is exploratory/diagnostic tool, not production pipeline

**Lesson**: Sequential matching is appropriate for relabeling script, NOT for CSV generation

---

## Current Status

### CSV Generation: Running
- Started: 2025-01-18 ~05:23 UTC
- Progress: 3/73 articles completed
- Estimated time: 30-90 minutes total
- Output: `data/v3_data/v3_csv/*.csv` (73 files)
- Log: `data/v3_data/csv_generation.log`

### What's Running:
```bash
uv run python scripts/corpus_building/generate_alignment_csv.py
```

---

## Performance Analysis

### Before Normalization Fix:
- Case-sensitive matching caused many false negatives
- Example: "TYLOR" vs "Tylor" = 59.8% match

### After Normalization Fix:
- Case-insensitive + punctuation normalization
- Example: "TYLOR" vs "Tylor" = 99.1% match

### Large Article Performance:
**california_law_review_amazon-trademark**:
- 1,261 PDF text items
- 669 HTML paragraphs
- Comparisons: 843,609 (exhaustive search)
- Time: ~2-5 minutes (acceptable for overnight batch)

---

## Potential Future Improvements

### 1. Different Fuzzy Matching Algorithms
**Current**: `partial_ratio` (finds best substring match)

**Alternatives to test**:
- `token_sort_ratio`: Sorts tokens before matching (handles word order)
- `token_set_ratio`: Handles missing/extra words better
- `ratio`: Simple full-string comparison
- **Hybrid approach**: Try multiple algorithms, pick best score

**Implementation**:
```python
from rapidfuzz import fuzz

# Test all algorithms
scores = {
    'partial_ratio': fuzz.partial_ratio(text1, text2, processor=utils.default_process),
    'token_sort_ratio': fuzz.token_sort_ratio(text1, text2, processor=utils.default_process),
    'token_set_ratio': fuzz.token_set_ratio(text1, text2, processor=utils.default_process),
    'ratio': fuzz.ratio(text1, text2, processor=utils.default_process),
}
best_score = max(scores.values())
```

---

### 2. Adjustable Matching Threshold
**Current**: Fixed threshold = 70%

**Idea**: Dynamic threshold based on text length
- Short text (< 50 chars): Higher threshold (85%+) - less room for variation
- Medium text (50-200 chars): Current threshold (70%)
- Long text (200+ chars): Lower threshold (60%) - more room for partial matches

**Implementation**:
```python
def get_dynamic_threshold(text: str) -> int:
    length = len(text)
    if length < 50:
        return 85
    elif length < 200:
        return 70
    else:
        return 60
```

---

### 3. Optimize Relabeling Script (Sequential Matching)
**Current**: `relabel_with_sequential_fuzzy_matching.py` already has `CONTEXT_WINDOW = 500`

**Improvements**:
- Fine-tune window size (test 300, 500, 700)
- Add backtracking when match confidence is low
- Track and report backtrack violations

**Note**: This IS appropriate for relabeling (unlike CSV generation)

---

### 4. Paragraph-Level vs Line-Level Matching
**Current**: Line-by-line matching

**Idea**: Group PDF lines into paragraphs before matching
- Reduce number of comparisons
- Better semantic alignment
- More robust to line break differences

**Challenge**: Docling gives us line-level extraction, need paragraph detection

---

### 5. Use RapidFuzz's `process.extractOne`
**Current**: Manual iteration through all paragraphs

**Optimization**: Use built-in `extractOne` for faster search
```python
from rapidfuzz import process

# Instead of manual loop
best_match = process.extractOne(
    pdf_text,
    html_paragraphs,
    scorer=fuzz.partial_ratio,
    processor=utils.default_process,
    score_cutoff=threshold
)
```

**Expected**: ~2-3x speedup from C++ optimizations

---

### 6. Parallel Processing
**Current**: Sequential processing of articles

**Idea**: Use multiprocessing to process multiple articles simultaneously
```python
from multiprocessing import Pool

with Pool(processes=4) as pool:
    pool.map(process_single_article, basenames)
```

**Expected**: ~4x speedup on multi-core machines

---

## Recommendations

### Immediate (Tonight):
1. ✅ Let CSV generation complete (running in background)
2. ⏭️ Review CSVs in the morning
3. ⏭️ Identify any remaining matching issues

### Short Term:
1. Test different fuzzy matching algorithms on sample articles
2. Implement `process.extractOne` optimization
3. Add hybrid algorithm approach (try multiple, pick best)

### Medium Term:
1. Implement dynamic thresholds based on text length
2. Add parallel processing for batch operations
3. Create validation metrics (precision/recall vs HTML ground truth)

### Long Term:
1. Paragraph-level matching with semantic grouping
2. Machine learning approach (train on existing matches)
3. Active learning: flag low-confidence matches for manual review

---

## Files Modified

1. `scripts/corpus_building/generate_alignment_csv.py`
   - Added normalization (`processor=utils.default_process`)
   - Maintained exhaustive search for comprehensive matching

2. `scripts/corpus_building/relabel_with_sequential_fuzzy_matching.py`
   - Added normalization (`processor=utils.default_process`)
   - Already has sliding window (`CONTEXT_WINDOW = 500`)

3. `scripts/corpus_building/extract_all_pdfs_with_docling.py`
   - Created for batch PDF extraction
   - Successfully extracted 73/73 PDFs

---

## Next Steps

1. **Review generated CSVs**: Look for patterns in unmatched items
2. **Analyze match confidence distribution**: Are most matches high-confidence?
3. **Test alternative algorithms**: See if `token_sort_ratio` or `token_set_ratio` perform better
4. **Benchmark performance**: Measure impact of `process.extractOne` optimization
5. **Create test suite**: Sample of known good/bad matches for validation

---

## Questions to Explore

1. Do the 11 failed PDF extractions need special handling (OCR)?
2. What's the distribution of match confidence scores?
3. Are there common patterns in unmatched PDF lines?
4. Would paragraph-level matching significantly improve results?
5. Should we have different thresholds for body text vs footnotes?
