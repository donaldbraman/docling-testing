# Model Training Guide

**Code Version:** 0.1.0
**Last Updated:** 2025-10-15

## Purpose

Complete guide to training DoclingBERT models for document structure classification.

## Prerequisites

- Python 3.13+
- GPU (Apple Silicon MPS or CUDA) recommended
- Training corpus (see [Data Collection](data-collection.md))
- Minimum 16GB RAM (32GB recommended for large batches)

## Training Workflows

### Workflow 1: Train Baseline Model

**Use when:** Starting from scratch with new corpus

```bash
# 1. Prepare corpus
python build_clean_corpus.py

# 2. Verify data distribution
python build_clean_corpus.py --analyze

# 3. Train baseline model (balanced weights)
python train_multiclass_classifier.py

# 4. Evaluate checkpoints
python evaluate_checkpoint.py --checkpoint models/doclingbert-v2/checkpoints/checkpoint-100
```

**Expected output:**
- Model checkpoints: `models/doclingbert-v2/checkpoints/`
- Final model: `models/doclingbert-v2/final_model/`
- Training logs: Console output + tensorboard logs

### Workflow 2: Rebalance for Recall

**Use when:** Baseline model has low body_text recall (< 80%)

```bash
# 1. Analyze baseline performance
python evaluate_checkpoint.py --checkpoint models/doclingbert-v2/checkpoints/checkpoint-100

# 2. Check FP:FN ratio
# Look for: "FP:FN ratio" in confusion matrix output

# 3. Train rebalanced model (3x body_text weight)
python train_rebalanced.py

# 4. Evaluate rebalanced model
python evaluate_checkpoint.py --checkpoint models/doclingbert-v2-rebalanced/checkpoints/checkpoint-100
```

**Class weight multipliers:**
- 2x: Conservative (small recall boost)
- 3x: Recommended (Issue #8 used this, achieved 83.3% recall)
- 5x: Aggressive (risk of overfitting)

### Workflow 3: Compare Models

**Use when:** Testing different hyperparameters or weights

```bash
# Compare multiple checkpoints
for ckpt in 25 50 75 100; do
  python evaluate_checkpoint.py \
    --checkpoint models/doclingbert-v2/checkpoints/checkpoint-$ckpt
done

# Save results
python evaluate_checkpoint.py --checkpoint <path> > results.txt
```

## Training Parameters

### Core Parameters (train_multiclass_classifier.py)

```python
training_args = TrainingArguments(
    max_steps=100,                    # Total training steps
    per_device_train_batch_size=1,   # Batch size per device
    learning_rate=2e-5,               # Learning rate
    eval_strategy="steps",            # Evaluate every N steps
    eval_steps=25,                    # Evaluation frequency
    save_steps=25,                    # Checkpoint frequency
    gradient_accumulation_steps=16,  # Effective batch size = 1*16 = 16
    gradient_checkpointing=True,     # Memory optimization
    seed=42,                          # Reproducibility
)
```

### Class Weights

Automatically calculated based on class imbalance:

```python
# Balanced weights (baseline)
class_weights = compute_class_weight(
    class_weight='balanced',
    classes=unique_labels,
    y=labels
)

# Rebalanced (Issue #8)
class_weights[body_text_id] *= 3.0  # 3x multiplier for body_text
```

**Current corpus distribution:**
- footnote: 31,809 samples (84.0%)
- body_text: 5,895 samples (15.6%)
- caption: 184 samples (0.5%)

**Imbalance ratio:** 5.4:1 (footnote:body_text)

## Training Monitoring

### Watch for These Metrics

**Good signs:**
- Training loss decreasing smoothly
- Validation accuracy improving
- No divergence between train and val loss

**Warning signs:**
- Val loss increasing while train loss decreases (overfitting)
- Loss plateauing early (learning rate too low)
- NaN losses (learning rate too high)

### Checkpoints

Models save every 25 steps:
```
models/doclingbert-v2/checkpoints/
├── checkpoint-25/
├── checkpoint-50/
├── checkpoint-75/
└── checkpoint-100/
```

Each contains:
- `config.json` - Model configuration
- `model.safetensors` - Model weights
- `trainer_state.json` - Training history
- `optimizer.pt` - Optimizer state

## Post-Training Evaluation

### Required Steps

1. **Evaluate final checkpoint:**
   ```bash
   python evaluate_checkpoint.py \
     --checkpoint models/doclingbert-v2/checkpoints/checkpoint-100
   ```

2. **Analyze confusion matrix:**
   - Check FP (false positives): footnote predicted as body_text
   - Check FN (false negatives): body_text predicted as footnote
   - Calculate FP:FN ratio: Target is 2:1 (prefer recall over precision)

3. **Document performance:**
   - Record metrics in `label_map.json`
   - Update model version history
   - Link to GitHub issue

### Success Criteria

**Baseline model:**
- Overall accuracy: ≥ 90%
- body_text F1: ≥ 70%
- Training stable (no NaN, no divergence)

**Rebalanced model:**
- body_text recall: ≥ 80%
- body_text F1: ≥ 80%
- FP:FN ratio: 1:1 to 2:1 (balanced to recall-optimized)

## Examples

### Example 1: Full Training Run (Issue #8)

```bash
# Step 1: Verify corpus
python build_clean_corpus.py
# Output: 37,888 paragraphs (7 classes)

# Step 2: Train rebalanced model
python train_rebalanced.py
# Training: 100 steps, ~20 minutes
# Loss: 4.68 → 2.46 (-47%)

# Step 3: Evaluate
python evaluate_checkpoint.py \
  --checkpoint models/doclingbert-v2-rebalanced/checkpoints/checkpoint-100

# Results:
# body_text recall: 83.3% ✅
# body_text F1: 84.08% ✅
# FP:FN ratio: 0.85:1 (close to 1:1)
```

### Example 2: Debugging Low Recall

```bash
# Problem: Baseline has 64.6% recall (too low)

# Step 1: Check confusion matrix
python evaluate_checkpoint.py --checkpoint <baseline>
# FN: 313 (missing 35% of body_text)
# FP: 74 (false positives acceptable)

# Step 2: Apply 3x weight multiplier
python train_rebalanced.py
# Trains new model with body_text_weight *= 3.0

# Step 3: Re-evaluate
python evaluate_checkpoint.py --checkpoint <rebalanced>
# FN: 148 (17% miss rate - improved!)
# Recall: 83.3% ✅
```

## Troubleshooting

### Issue: Training Hangs at Evaluation

**Symptoms:** Step completes but evaluation stuck at 41%

**Causes:**
- MPS (Apple Silicon GPU) deadlock
- Memory pressure
- Concurrent processes using GPU

**Solutions:**
1. Kill stuck process: `ps aux | grep python`
2. Reduce batch size: `per_device_eval_batch_size=4`
3. Disable MPS: `PYTORCH_ENABLE_MPS_FALLBACK=1 python train.py`

### Issue: Low Recall Despite High Accuracy

**Symptoms:** 95% accuracy but 65% body_text recall

**Causes:**
- Class imbalance (footnote dominates training)
- Model optimizing for majority class

**Solutions:**
1. Increase body_text class weight (2x → 3x → 5x)
2. Adjust classification threshold (0.5 → 0.4)
3. Collect more body_text samples

### Issue: Model Overfitting

**Symptoms:** Train loss ↓, Val loss ↑

**Solutions:**
1. Reduce training steps (100 → 75)
2. Increase dropout (add to model config)
3. Collect more diverse training data

## Related Guides

- [Model Evaluation](model-evaluation.md) - Metrics analysis
- [Data Collection](data-collection.md) - Building training corpus
- [cite-assist Integration](cite-assist-integration.md) - Model deployment

---

**Last Updated:** 2025-10-15
