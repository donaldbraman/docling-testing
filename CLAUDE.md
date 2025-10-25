# Claude Code Instructions for body-extractor

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

**🚀 Start here:** [guides/TRAINING_QUICK_START.md](docs/guides/TRAINING_QUICK_START.md) - Complete training workflow with cite-assist integration

**Read only what you need, when you need it:**

| Topic | Guide | Read When |
|-------|-------|-----------|
| **Training Workflow** | **[TRAINING_QUICK_START.md](docs/guides/TRAINING_QUICK_START.md)** | **Starting any training task** |
| **GPU Testing (vast.ai)** | **[VASTAI_QUICK_START.md](docs/VASTAI_QUICK_START.md)** | **Testing OCR pipeline on cloud GPU** |
| Model Training Details | [model-training.md](docs/guides/model-training.md) | Deep dive into training parameters |
| Data Collection | [data-collection.md](docs/guides/data-collection.md) | Scraping PDFs or building corpus |
| Model Evaluation | [model-evaluation.md](docs/guides/model-evaluation.md) | Evaluating checkpoints or comparing models |
| Troubleshooting | [troubleshooting.md](docs/guides/troubleshooting.md) | Common issues and solutions |
| vast.ai Best Practices | [VASTAI_BEST_PRACTICES.md](docs/VASTAI_BEST_PRACTICES.md) | Debugging vast.ai infrastructure issues |
| RunPod Setup | [RUNPOD_SETUP_GUIDE.md](docs/RUNPOD_SETUP_GUIDE.md) | Alternative GPU cloud provider |

**Deployment guides:** See `cite-assist/docs/guides/` for deployment, integration, and production serving

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

## Development Tools

**Astral Suite (uv, ruff, typer):** Modern Python development tools

**Details:** [docs/ASTRAL_SUITE_GUIDE.md](docs/ASTRAL_SUITE_GUIDE.md)

**Quick commands:**
```bash
# Install dependencies
uv sync

# Add new package
uv add package-name

# Run scripts
uv run python script.py

# Lint and format
ruff check --fix . && ruff format .
```

---

## Development Guidelines

- **Always use uv** - Never use pip directly (10-100x faster, deterministic)
- **Always use feature branches** - No direct commits to master
- **Link changes to issues** - Create detailed GitHub issues before implementing
- **Run tests before committing** - `uv run pytest` or `uv run pytest -v` for detailed output
- **Test with real PDFs** - Use law review PDFs from data/raw_pdf/
- **Version models** - Include metadata in label_map.json (model_name, version, base_model)
- **Document metrics** - Record F1, recall, precision for all models
- **Validate models** - Run `uv run python scripts/utilities/validate_model_metadata.py` before deployment
- **GitHub labels** - See `~/.claude/guides/github-labels.md` for label auto-generation guidance

### Testing

Run tests with pytest (always use uv):
```bash
# Run all fast tests (excludes slow model loading tests)
uv run pytest -m "not slow"

# Run all tests including slow ones
uv run pytest

# Run with verbose output
uv run pytest -v

# Run specific test file
uv run pytest tests/test_models.py

# Run with coverage report
uv run pytest --cov=scripts --cov-report=html
```

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

**Current corpus:** 254 clean PDFs (207 law reviews + 47 arXiv STEM papers)
- **Platform covers:** 0 (all removed)
- **Diversity:** 18.5% non-law content (reduces overfitting)
- **Status:** ✅ Ready for training

**Labeled samples:** 37,888 paragraphs across 7 semantic classes
- Semantic PDF tags: 31,809 samples (highest quality)
- HTML-PDF matching: 1,733 samples
- Cover page patterns: 2,340 samples

**Available for expansion:**
- Additional arXiv papers: Run `uv run python scripts/data_collection/collect_arxiv_papers.py --target 100` for 30% STEM diversity
- Additional law reviews: ~500+ PDFs available (UCLA, Georgetown, Texas)
- **Estimated gain:** ~26,000 body_text samples

---

## Training Best Practices

### Before Training
1. Check data distribution: `uv run python scripts/corpus_building/build_clean_corpus.py --analyze`
2. Verify corpus quality: No duplicate texts, balanced labels
3. Set class weights based on imbalance ratio

### During Training
1. Monitor checkpoints at steps 25, 50, 75, 100
2. Watch for overfitting (val_loss should decrease)
3. Track body_text recall vs precision trade-off

### After Training
1. Evaluate all checkpoints: `uv run python scripts/evaluation/evaluate_checkpoint.py --checkpoint <path>`
2. Generate confusion matrix
3. Calculate FP:FN ratio for body_text
4. Document metrics in label_map.json
5. Validate metadata: `uv run python scripts/utilities/validate_model_metadata.py`

---

*Last updated: 2025-10-15*
