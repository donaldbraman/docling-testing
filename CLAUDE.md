# Claude Code Instructions for docling-testing

**Project Purpose:** ML model training repository for document structure classification

**Note:** Global instructions are in `~/CLAUDE.md` (symlinked from cross-repo). This file contains **project-specific** instructions only.

## Quick Reference

**Active Models:**
- DoclingBERT v2-rebalanced (83.3% body_text recall)
- Location: `models/doclingbert-v2-rebalanced/final_model/`

**Core Training Scripts:**
- scripts/training/train_multiclass_classifier.py - 7-class DoclingBERT training
- scripts/training/train_rebalanced.py - Rebalanced weights for recall optimization
- scripts/evaluation/evaluate_checkpoint.py - Model evaluation with confusion matrix

**Data Collection:**
- scripts/data_collection/scrape_law_reviews.py - Multi-journal scraping
- scripts/corpus_building/build_clean_corpus.py - Corpus construction from multiple sources

---

## Just-In-Time Guides

**Read only what you need, when you need it:**

| Topic | Guide | Read When |
|-------|-------|-----------|
| Model Training | [guides/model-training.md](docs/guides/model-training.md) | Training new models or rebalancing |
| Data Collection | [guides/data-collection.md](docs/guides/data-collection.md) | Scraping PDFs or building corpus |
| Model Evaluation | [guides/model-evaluation.md](docs/guides/model-evaluation.md) | Evaluating checkpoints or comparing models |
| Integration | [guides/cite-assist-integration.md](docs/guides/cite-assist-integration.md) | Deploying models to cite-assist |
| Troubleshooting | [guides/troubleshooting.md](docs/guides/troubleshooting.md) | Common issues and solutions |

**Full guide index:** [docs/guides/README.md](docs/guides/README.md)

---

## Scripts Organization

All scripts are organized in `scripts/` subdirectories by purpose:

- **scripts/training/** - Model training scripts (5 scripts)
- **scripts/evaluation/** - Model evaluation and testing (3 scripts)
- **scripts/corpus_building/** - Corpus creation and processing (14 scripts)
- **scripts/data_collection/** - PDF scraping and downloading (17 scripts)
- **scripts/analysis/** - Analysis and inspection tools (14 scripts)
- **scripts/testing/** - Test scripts and benchmarks (10 scripts)
- **scripts/experiments/** - Experimental scripts (2 scripts)
- **scripts/utilities/** - Helper utilities (6 scripts)

---

## Development Guidelines

- **Always use feature branches** - No direct commits to master
- **Link changes to issues** - Create detailed GitHub issues before implementing
- **Test with real PDFs** - Use law review PDFs from data/raw_pdf/
- **Version models** - Include metadata in label_map.json (model_name, version, base_model)
- **Document metrics** - Record F1, recall, precision for all models
- **Validate models** - Run `python scripts/utilities/validate_model_metadata.py` before deployment
- **GitHub labels** - See `~/.claude/guides/github-labels.md` for label auto-generation guidance

---

## Model Versioning

**Current production model:** v2-rebalanced
- Issue: #8 (Improve body_text recall: rebalance class weights for 2:1 FP:FN ratio)
- Metrics:
  - body_text recall: 83.3%
  - body_text F1: 84.08%
  - Overall accuracy: 94.7%
- Training: 100 steps, 3x body_text weight multiplier
- Base: ModernBERT-base (149M parameters)

**Model history:**
- v2-rebalanced (current) - Issue #8
- v2-quick-test (baseline) - Issue #7
- v1 (binary footnote classifier) - Issue #4 (superseded)

---

## Data Sources

**Current corpus:** 37,888 paragraphs across 7 semantic classes

**Sources:**
- Semantic PDF tags (31,809 samples) - Highest quality
- HTML-PDF matching (1,733 samples)
- Cover page patterns (2,340 samples)

**Available for expansion:**
- UCLA Law Review: ~150 more PDFs
- Georgetown Law: ~200 PDFs
- Texas Law: ~180 PDFs
- Annual Reviews: ~300 PDFs
- **Total available:** ~800+ PDFs (~26,000 estimated body_text samples)

---

## Training Best Practices

### Before Training
1. Check data distribution: `python scripts/corpus_building/build_clean_corpus.py --analyze`
2. Verify corpus quality: No duplicate texts, balanced labels
3. Set class weights based on imbalance ratio

### During Training
1. Monitor checkpoints at steps 25, 50, 75, 100
2. Watch for overfitting (val_loss should decrease)
3. Track body_text recall vs precision trade-off

### After Training
1. Evaluate all checkpoints: `python scripts/evaluation/evaluate_checkpoint.py --checkpoint <path>`
2. Generate confusion matrix
3. Calculate FP:FN ratio for body_text
4. Document metrics in label_map.json
5. Validate metadata: `python scripts/utilities/validate_model_metadata.py`

---

*Last updated: 2025-10-15*
