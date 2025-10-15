# Model Evaluation Guide

**Code Version:** 0.1.0
**Last Updated:** 2025-10-15

## Purpose

Guide to evaluating DoclingBERT checkpoints and analyzing model performance.

## Quick Start

```bash
# Evaluate specific checkpoint
python evaluate_checkpoint.py \
  --checkpoint models/doclingbert-v2-rebalanced/checkpoints/checkpoint-100

# Compare all checkpoints
for ckpt in 25 50 75 100; do
  python evaluate_checkpoint.py \
    --checkpoint models/doclingbert-v2/checkpoints/checkpoint-$ckpt \
    | tee eval_ckpt$ckpt.log
done
```

## Key Metrics

### Overall Metrics
- **Accuracy**: Percentage of correct predictions
- **F1 Macro**: Unweighted average of per-class F1 scores
- **F1 Weighted**: Weighted by class support

### Per-Class Metrics (body_text focus)
- **Precision**: % of predicted body_text that are actually body_text
- **Recall**: % of actual body_text that are correctly identified
- **F1 Score**: Harmonic mean of precision and recall

### FP:FN Ratio Analysis
- **FP (False Positives)**: Footnotes incorrectly classified as body_text
- **FN (False Negatives)**: Body_text incorrectly classified as footnote
- **Ratio**: FP/FN (target: 1.5:1 to 2:1 for recall-optimized models)

## Understanding Confusion Matrix

```
True \ Pred  body_text  footnote  caption
body_text         737       148        0    ← 737 correct, 148 missed
footnote          126      4646        0    ← 126 false positives
caption             5        22        0
```

**Interpretation:**
- **Diagonal** = Correct predictions
- **Row totals** = Ground truth class sizes
- **Column totals** = Predicted class distributions

**For body_text:**
- True Positives (TP): 737
- False Negatives (FN): 148 (missed body_text)
- False Positives (FP): 126 (footnotes misclassified)
- Recall: 737 / (737 + 148) = 83.3%
- Precision: 737 / (737 + 126) = 85.4%

## Evaluation Checklist

- [ ] Run evaluation on final checkpoint (checkpoint-100)
- [ ] Check body_text recall ≥ 80%
- [ ] Check body_text F1 ≥ 80%
- [ ] Analyze FP:FN ratio (target: 1:1 to 2:1)
- [ ] Compare to baseline model
- [ ] Document results in label_map.json
- [ ] Update version history

## Interpreting Results

### Scenario 1: High Accuracy, Low Recall

```
Accuracy: 95%
body_text recall: 65%
FP:FN ratio: 1:4.2
```

**Problem:** Model optimizing for majority class (footnote)

**Solution:** Rebalance class weights (see [Model Training](model-training.md))

### Scenario 2: High Recall, Low Precision

```
Recall: 90%
Precision: 70%
FP:FN ratio: 3:1
```

**Problem:** Too aggressive (many false positives)

**Solution:** Reduce class weight multiplier or adjust threshold

### Scenario 3: Balanced Performance (Goal)

```
Recall: 83.3%
Precision: 85%
F1: 84%
FP:FN ratio: 0.85:1
```

**Status:** Production-ready ✅

## Related Guides

- [Model Training](model-training.md) - Training workflows
- [cite-assist Integration](cite-assist-integration.md) - Deployment

---

**Last Updated:** 2025-10-15
