# DoclingBERT Training Quick Start

**Repository:** docling-testing (training)
**Deployment:** cite-assist (production)
**Last Updated:** 2025-10-17

---

## Training Workflow

```
[1. Prepare Corpus] → [2. Train Model] → [3. Evaluate] → [4. Deploy to cite-assist]
    ↓ this repo         ↓ this repo      ↓ this repo    ↓ cite-assist repo
```

---

## Step 1: Prepare Training Corpus

### Current Corpus Status
```bash
# Check corpus
uv run python scripts/corpus_building/build_clean_corpus.py --analyze

# Expected output:
# Total PDFs: 254 clean (207 law + 47 arXiv)
# Platform covers: 0 (removed)
# Diversity: 18.5% non-law
```

### Corpus Building

**See:** [data-collection.md](data-collection.md) for detailed scraping guides

**Quick commands:**
```bash
# Expand law review corpus
uv run python scripts/data_collection/scrape_ucla_law_review.py --target 20

# Add more STEM diversity
uv run python scripts/data_collection/collect_arxiv_papers.py --target 100

# Build final corpus
uv run python scripts/corpus_building/build_clean_corpus.py
```

---

## Step 2: Train DoclingBERT Classifier

### Training Script

**Location:** `scripts/training/train_multiclass_classifier.py`

**Basic training:**
```bash
uv run python scripts/training/train_multiclass_classifier.py \
    --model modernbert-base \
    --output models/doclingbert-v3 \
    --steps 100 \
    --batch-size 8
```

**With class rebalancing (for recall optimization):**
```bash
uv run python scripts/training/train_rebalanced.py \
    --model modernbert-base \
    --output models/doclingbert-v3.1-rebalanced \
    --steps 100 \
    --body-text-weight-multiplier 3.0
```

### Training Configuration

**Default hyperparameters:**
- Base model: ModernBERT-base (149M params)
- Training steps: 100
- Learning rate: 2e-5
- Batch size: 8
- Evaluation: Every 25 steps

**See full details:** [model-training.md](model-training.md)

---

## Step 3: Evaluate Model

### Evaluation Script

**Location:** `scripts/evaluation/evaluate_checkpoint.py`

**Evaluate checkpoint:**
```bash
uv run python scripts/evaluation/evaluate_checkpoint.py \
    --checkpoint models/doclingbert-v3/checkpoint-100 \
    --corpus data/labeled_pdf_corpus.csv
```

**Output:**
- Confusion matrix
- Per-class precision/recall/F1
- Overall accuracy
- FP:FN ratio for body_text

### Model Selection Criteria

**For production deployment:**
- Body text recall: ≥80% (minimize false negatives)
- Overall accuracy: ≥95%
- FP:FN ratio: ~2:1 (prefer false positives over false negatives)

**See full evaluation guide:** [model-evaluation.md](model-evaluation.md)

---

## Step 4: Deploy to cite-assist

**This step happens in the cite-assist repository.**

### Deployment Guides (cite-assist repo)

**📍 Location:** `cite-assist/docs/guides/`

1. **[classifier-service.md](https://github.com/your-org/cite-assist/blob/main/docs/guides/classifier-service.md)**
   - API reference for classifier service
   - Integration examples
   - Performance characteristics

2. **[doclingbert-upgrade.md](https://github.com/your-org/cite-assist/blob/main/docs/guides/doclingbert-upgrade.md)**
   - Step-by-step deployment guide
   - Incremental upgrade process
   - Rollback procedures

3. **[model-upgrade-workflow.md](https://github.com/your-org/cite-assist/blob/main/docs/guides/model-upgrade-workflow.md)**
   - General upgrade patterns
   - Blue-green deployment strategies
   - Version tracking

### Quick Deployment Steps

**In cite-assist repository:**

```bash
# 1. Copy trained model to cite-assist
cp -r ../docling-testing/models/doclingbert-v3 ./models/

# 2. Update service configuration
# Edit: services/classifier/config.py
# Change: MODEL_PATH = "models/doclingbert-v3"

# 3. Test locally
docker-compose up classifier-service

# 4. Deploy to production
# Follow: docs/guides/doclingbert-upgrade.md
```

**For detailed deployment:** See cite-assist repository guides above.

---

## Training Best Practices

### Before Training
- ✅ Verify corpus quality (no platform covers)
- ✅ Check class distribution balance
- ✅ Set appropriate class weights for recall goals
- ✅ Choose low-GPU-usage time if sharing resources

### During Training
- ✅ Monitor checkpoint evaluations (steps 25, 50, 75, 100)
- ✅ Watch for overfitting (val_loss should decrease)
- ✅ Track body_text recall vs precision trade-off

### After Training
- ✅ Evaluate all checkpoints
- ✅ Select best model based on production criteria
- ✅ Document metrics in model metadata
- ✅ Test on held-out samples before deployment

---

## Model Versioning

**Version naming convention:** `doclingbert-vX.Y[-variant]`

**Examples:**
- `doclingbert-v2` - Binary footnote classifier (superseded)
- `doclingbert-v3-spatial` - 7-class spatial classifier (current production)
- `doclingbert-v3.1-rebalanced` - Rebalanced for 83.3% body_text recall (candidate)

**Metadata requirements:**
```json
{
  "model_name": "doclingbert-v3.1-rebalanced",
  "version": "3.1",
  "base_model": "answerdotai/ModernBERT-base",
  "parameters": "149M",
  "training_steps": 100,
  "accuracy": 0.947,
  "body_text_recall": 0.833,
  "body_text_f1": 0.8408,
  "created_at": "2025-10-17"
}
```

**See:** [code-versioning.md](code-versioning.md) for version management

---

## Troubleshooting

### Training Issues

**See:** [troubleshooting.md](troubleshooting.md) for common training problems

**Quick fixes:**
- Out of memory: Reduce batch size to 4 or 2
- Poor recall: Increase body_text class weight
- Overfitting: Reduce training steps or add more data

### Deployment Issues

**See cite-assist guides:**
- [doclingbert-upgrade.md](https://github.com/your-org/cite-assist/blob/main/docs/guides/doclingbert-upgrade.md) - Deployment troubleshooting
- [classifier-service.md](https://github.com/your-org/cite-assist/blob/main/docs/guides/classifier-service.md) - Service issues

---

## Related Documentation

### In This Repo (docling-testing)
- [model-training.md](model-training.md) - Detailed training guide
- [model-evaluation.md](model-evaluation.md) - Evaluation procedures
- [data-collection.md](data-collection.md) - Corpus building
- [troubleshooting.md](troubleshooting.md) - Common issues

### In cite-assist Repo
- [classifier-service.md](../../../cite-assist/docs/guides/classifier-service.md) - Deployment API reference
- [doclingbert-upgrade.md](../../../cite-assist/docs/guides/doclingbert-upgrade.md) - Deployment guide
- [model-upgrade-workflow.md](../../../cite-assist/docs/guides/model-upgrade-workflow.md) - Upgrade patterns

---

## Repository Boundary

**This repo (docling-testing):** Training, evaluation, corpus building
**cite-assist repo:** Deployment, production serving, integration

**Model handoff point:**
Trained model in `models/doclingbert-vX/` → Copy to `cite-assist/models/`

---

**Version:** 1.0
**Created:** 2025-10-17
🤖 Generated with [Claude Code](https://claude.com/claude-code)
