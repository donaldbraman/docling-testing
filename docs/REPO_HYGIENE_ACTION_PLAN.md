# Repository Hygiene Action Plan

**Generated:** October 17, 2025
**Status:** Action Required

---

## Executive Summary

Repository hygiene audit completed. Found:
- ✅ **21 active collections** with PDFs
- ⚠️ **19 stale collection logs** (no PDFs) - need cleanup
- 📄 **30 recent docs** (≤1 day old) - need git commit review
- 🗑️ **Test data directories** (4.6 MB) - may archive
- 🔧 **33 collection scripts** - check for duplicates

---

## Priority Actions

### Priority 1: Git Commits (Immediate)

**Untracked Important Files:**
```bash
# Commit these immediately - critical documentation
git add docs/CORPUS_PLATFORM_COVER_CLEANING_REPORT.md
git add docs/NON_LAW_COLLECTION_DEPLOYMENT_SUMMARY.md

# Commit successful arXiv collection logs
git add data/collection_logs/arxiv/

# Decision needed: PubMed Central (failed collection)
# Option A: Delete (collection failed, no PDFs)
# Option B: Keep as documentation of failure
```

**Recent Documentation to Review:**
- 30 recently modified docs (all from Oct 16-17)
- Most are reports and guides from recent work
- Should audit which are tracked vs untracked

### Priority 2: Cleanup Stale Collection Logs (High)

**19 Stale Directories (logs but no PDFs):**

These have log files but zero PDFs collected. Likely failed attempts:

```bash
# Failed law review collections (0 PDFs)
data/collection_logs/arizona_law_review/
data/collection_logs/boston_college_law_review/
data/collection_logs/boston_university_law_review/
data/collection_logs/cornell_law_review/
data/collection_logs/fordham_law_review/
data/collection_logs/george_washington_law_review/
data/collection_logs/illinois_law_review/
data/collection_logs/iowa_law_review/
data/collection_logs/minnesota_law_review/
data/collection_logs/notre_dame_law_review/
data/collection_logs/nyu_law_review/
data/collection_logs/rutgers_law_review/
data/collection_logs/southern_california_law_review/
data/collection_logs/university_of_chicago_law_review/
data/collection_logs/upenn_law_review/
data/collection_logs/vanderbilt_law_review/
data/collection_logs/washington_law_review/
data/collection_logs/washington_university_law_review/

# Failed non-law collection
data/collection_logs/pubmed_central/  # 0 PDFs, collection failed
```

**Recommendation:**
- **DELETE** these directories - they're failed collection attempts with no value
- Keep only successful collections (21 active logs)
- This reduces clutter from 40 → 21 directories

### Priority 3: Remove Corrupted PDF (High)

```bash
rm data/raw_pdf/bu_law_review_online_harassment_intermediary_immunity.pdf
```

**Issue:** Invalid PDF header (HTML file misnamed as PDF)
**Impact:** Cannot be used for training

### Priority 4: Test Data Cleanup (Medium)

**Test Directories:**
```
data/cover_pages/test_sample/          (3 files, 0.1 MB)
data/cover_pages/verified_covers/source_pdfs_cover_page_only/  (85 files, 4.5 MB)
```

**Decision needed:**
- Are these still used for testing?
- Should they be archived?
- Can they be deleted?

### Priority 5: Documentation Review (Medium)

**Recent Docs (30 files from Oct 16-17):**

These may need git commits:
- CORPUS_CONSOLIDATION_REPORT.md
- CORPUS_DIVERSITY_ASSESSMENT.md
- CORPUS_PLATFORM_COVER_CLEANING_REPORT.md
- CURRENT_DATASET_ACTION_PLAN.md
- DATA_SIZING_QUICK_REFERENCE.md
- DATA_SIZING_RESEARCH_SUMMARY.md
- EMPIRICAL_DATA_SIZING_RESEARCH.md
- NON_LAW_COLLECTION_DEPLOYMENT_SUMMARY.md (untracked)
- NON_LAW_REVIEW_COLLECTION_DEPLOYMENT_PLAN.md
- PLATFORM_COVER_DETECTION_COMPLETE.md
- QUICK_START_NON_LAW_COLLECTION.md
- And 19 others...

**Older Docs (>3 days old):**

May be stale or superseded:
- BENCHMARK_PLAN.md (3 days old)
- CONTINUATION_PROMPT.md (3 days old)
- HTML_EXTRACTION_PATTERNS.md (3 days old)
- IMPLEMENTATION_PLAN.md (3 days old)
- RESEARCH_TEXT_CLASSIFICATION_METHODS.md (3 days old)

**Action:** Review for staleness and consider archiving

### Priority 6: Scripts Audit (Low)

**Collection Scripts:**
- 14 `collect_*.py` scripts
- 12 `scrape_*.py` scripts
- Total: 26 collection scripts

**Potential duplicates to check:**
- Do we have both `collect_X.py` and `scrape_X.py` for same source?
- Are old collection scripts still needed?
- Should failed scripts be archived?

---

## Recommended Cleanup Script

```bash
#!/bin/bash
# Repository Hygiene Cleanup Script

echo "=== Repository Cleanup ==="

# 1. Remove stale collection logs (no PDFs)
echo "Removing stale collection logs..."
rm -rf data/collection_logs/arizona_law_review/
rm -rf data/collection_logs/boston_college_law_review/
rm -rf data/collection_logs/boston_university_law_review/
rm -rf data/collection_logs/cornell_law_review/
rm -rf data/collection_logs/fordham_law_review/
rm -rf data/collection_logs/george_washington_law_review/
rm -rf data/collection_logs/illinois_law_review/
rm -rf data/collection_logs/iowa_law_review/
rm -rf data/collection_logs/minnesota_law_review/
rm -rf data/collection_logs/notre_dame_law_review/
rm -rf data/collection_logs/nyu_law_review/
rm -rf data/collection_logs/rutgers_law_review/
rm -rf data/collection_logs/southern_california_law_review/
rm -rf data/collection_logs/university_of_chicago_law_review/
rm -rf data/collection_logs/upenn_law_review/
rm -rf data/collection_logs/vanderbilt_law_review/
rm -rf data/collection_logs/washington_law_review/
rm -rf data/collection_logs/washington_university_law_review/
rm -rf data/collection_logs/pubmed_central/

# 2. Remove corrupted PDF
echo "Removing corrupted PDF..."
rm -f data/raw_pdf/bu_law_review_online_harassment_intermediary_immunity.pdf

# 3. Git add important reports
echo "Staging important reports..."
git add docs/CORPUS_PLATFORM_COVER_CLEANING_REPORT.md
git add docs/NON_LAW_COLLECTION_DEPLOYMENT_SUMMARY.md
git add data/collection_logs/arxiv/

echo "=== Cleanup Complete ==="
echo ""
echo "Next steps:"
echo "1. Review git status"
echo "2. Review test data directories (data/cover_pages/)"
echo "3. Commit staged files"
```

---

## Impact Analysis

### Before Cleanup:
- Collection logs: 40 directories
- PDFs: 255 total
- Untracked files: Many
- Test data: 4.6 MB

### After Cleanup:
- Collection logs: 21 directories (active only)
- PDFs: 254 total (removed 1 corrupted)
- Untracked files: Reduced significantly
- Test data: TBD (pending review)

**Storage saved:** ~1-2 MB (mostly small log files)
**Organization gain:** 47.5% reduction in log directories (40 → 21)

---

## Next Steps

1. **Execute cleanup script** (or run commands manually)
2. **Review test data** - decide keep/archive/delete
3. **Audit documentation** - commit important docs, archive/delete stale ones
4. **Review collection scripts** - identify duplicates/deprecated scripts
5. **Update .gitignore** - ensure proper tracking

---

## Notes

**Stale logs are safe to delete because:**
- They have 0 PDFs (collection failed)
- They're recent (0 days old) - not historical data
- They can be regenerated if needed by re-running collection scripts
- They're not tracked in git

**Corrupted PDF is safe to delete because:**
- It's not a valid PDF (HTML file misnamed)
- Cannot be used for training
- Can be re-downloaded if needed (BU Law Review source)

---

**Last Updated:** October 17, 2025
**Action Required:** Yes
**Estimated Time:** 10 minutes
