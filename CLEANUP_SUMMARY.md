# Cleanup Summary - October 22, 2025

## Overview

Completed comprehensive cleanup and archiving of unused code and data to reduce clutter and improve maintainability.

## What Was Archived

### Archive Location
`archive_20251022/` (3.6 GB)

### Archived Items
- **27 Python scripts** - Exploratory/debug scripts and old versions
  - 16 top-level scripts (analyze_*, debug_*, test_*)
  - 7 evaluation scripts (explain_*, debug_matching)
  - 4 corpus building scripts (generate_alignment_csv v2-v5)

- **18 log files** - Historical execution logs
  - OCR investigation logs
  - Evaluation run logs
  - Pipeline testing logs

- **22 results directories** - Old experiment results
  - benchmark_test, body_extraction, comparisons
  - confusion_matrices, diffs, experiment_2
  - features, gemini, grayscale_fix_test
  - layout_analysis (v1 & v2), ocr_comparison
  - ocr_parameter_tests, ocr_pipeline_per_pdf
  - ocr_pipeline_test, overlay_pdfs
  - paddleocr_test, saved_vs_fresh
  - sequence_alignment, spatial, temp_images
  - test_restructured

- **Orphan files** - Loose log/HTML/PDF files from results/

## What Was Kept

### Core Code
- `src/docling_testing/` - **NEW** shared library
  - `core/ocr.py` - OCR engine configuration
  - `core/pdf_utils.py` - PDF manipulation
  - `core/extraction.py` - Text extraction
  - `core/metrics.py` - Evaluation metrics

- `scripts/training/` - All 7 training scripts
- `scripts/evaluation/evaluate_checkpoint.py` - Core evaluation
- `scripts/corpus_building/` - Active corpus scripts
- `scripts/data_collection/` - All 17 collection scripts
- `experiments/` - Organized exploratory work with documentation

### Active Data
- `results/ocr_pipeline_evaluation/` - Current baseline
- `results/tesseract_corpus_pipeline/` - Current OCR work
- `results/dpi_test/` - Recent experiment
- `data/v3_data/` - All training data

### Key Documentation
- `CLAUDE.md` - Project instructions
- `docs/guides/` - Training and evaluation guides
- `experiments/README.md` - Experiment organization
- `REFACTORING_SUMMARY.md` - Refactoring details

## Impact

### Before Cleanup
```
Working directory:
  - 111 Python files total
  - 23 top-level scripts
  - 72 evaluation scripts
  - 25 results directories
  - 18 log files scattered
```

### After Cleanup
```
Working directory:
  - 0 top-level scripts (100% cleanup)
  - 3 active results directories (88% reduction)
  - 0 scattered log files (100% cleanup)
  - 65 evaluation scripts (10% reduction)
  - All code organized in src/, scripts/, experiments/
```

### Benefits
1. **Cleaner workspace** - No exploratory scripts in root directory
2. **Clear organization** - Production code vs experiments clearly separated
3. **Reduced duplication** - Shared library eliminates repeated patterns
4. **Better navigation** - Easy to find current vs historical work
5. **Preserved history** - All work archived with comprehensive index

## Archive Access

To retrieve archived files:

```bash
# View archive index
cat archive_20251022/ARCHIVE_INDEX.md

# Copy back a specific file
cp archive_20251022/scripts/top_level/test_single_document.py .

# Browse archive
ls -R archive_20251022/
```

## Related Changes

This cleanup is part of a larger refactoring effort:

1. **Shared Library** - Created `src/docling_testing/` package
   - See `REFACTORING_SUMMARY.md` for details
   - Replaces ~450 lines of duplicated code

2. **Experiments Organization** - Structured exploratory work
   - See `experiments/README.md` for guidelines
   - Documents hypothesis, methodology, findings

3. **Archive Strategy** - Preserve without cluttering
   - See `archive_20251022/ARCHIVE_INDEX.md` for contents
   - Can be git-ignored or committed based on preference

## Next Steps

### Recommended
1. ✅ Run tests to ensure nothing broken: `uv run pytest`
2. ✅ Verify core scripts still work
3. Update `.gitignore` if archiving future experiments
4. Consider adding archive to `.gitignore` (3.6 GB)

### Optional
5. Migrate more scripts to use shared library
6. Add tests for shared library utilities
7. Further consolidate overlapping evaluation scripts

## File Retention Policy

Going forward:

**Keep in main workspace:**
- Production code (training, evaluation, data collection)
- Active experiments (experiments/YYYY-MM-DD_topic/)
- Current results (results/*/most recent)
- Core documentation

**Move to archive:**
- Exploratory scripts after findings documented
- Old experiment results after >3 months
- Superseded versions (v1, v2, etc.)
- Execution logs after findings extracted

---

**Archive created:** 2025-10-22
**Space saved:** 3.6 GB
**Files archived:** 67+ files/directories
**Documentation:** Full index in `archive_20251022/ARCHIVE_INDEX.md`
