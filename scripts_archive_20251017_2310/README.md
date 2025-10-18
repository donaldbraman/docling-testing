# Scripts Archive - 2025-01-17 23:10

This archive contains old scripts that are no longer needed for the V3 pipeline but are preserved for historical reference.

## Archived Directories

### analysis/ (32 scripts)
- Corpus analysis scripts used during exploration phase
- HTML structure investigation
- Footnote pattern surveys
- Label comparison and validation
- **Status**: Analysis complete, no longer needed

### data_collection/ (36 scripts)
- Web scraping scripts for law review PDFs and HTML
- Journal-specific download scripts
- Integration scripts for various sources
- **Status**: Data collection complete, corpus established

### experiments/ (4 scripts)
- Experimental code for testing ideas
- **Status**: Completed experiments

### testing/ (16 scripts)
- Test scripts for various extraction methods
- Benchmarking and validation tests
- **Status**: Testing complete

### corpus_building_old/ (28 scripts)
- Old corpus building scripts from V1 and V2
- Spatial corpus builders
- PDF tag extraction (pre-v3)
- HTML-PDF matching (legacy approach)
- Visualization tools
- **Status**: Replaced by V3 pipeline

### utilities_old/ (43 scripts)
- One-off validation scripts for specific journals
- Integration scripts for specific data sources
- Diagnostic and debugging scripts
- Repository hygiene tools
- **Status**: One-time tasks completed

## Active V3 Pipeline Scripts (Kept)

### corpus_building/
- `relabel_with_sequential_fuzzy_matching.py` - Core V3 relabeling script

### utilities/
- `extract_html_positive_inclusion.py` - HTML ground truth extraction
- `validate_model_metadata.py` - Model validation

### training/ (8 scripts)
- ModernBERT training scripts
- Evaluation scripts
- Active training pipeline

### deployment/ (4 scripts)
- Production deployment scripts
- Collection tracking and orchestration

## Archive Statistics

- **Total archived**: ~189 scripts
- **Total kept**: 16 active scripts
- **Archive size**: 1.3 MB
- **Reduction**: ~91% reduction in script count

## Recovery

All archived scripts are preserved and can be referenced or recovered if needed:
```bash
# View archived script
cat scripts_archive_20251017_2310/analysis/analyze_html_structure.py

# Restore a script if needed
cp scripts_archive_20251017_2310/utilities_old/some_script.py scripts/utilities/
```

---
*Archived: 2025-01-17 23:10*
*Reason: V3 pipeline cleanup - removed obsolete scripts*
