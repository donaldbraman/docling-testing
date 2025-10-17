# Data Sizing Quick Reference Guide

**For:** Document classification with pre-trained transformers
**Last Updated:** October 16, 2025

---

## At-a-Glance Thresholds

### Samples Per Class

| Tier | Samples/Class | Total (7 classes) | Quality | Purpose |
|------|---------------|-------------------|---------|---------|
| **Minimum Viable** | 100-200 | 700-1,400 | High | POC, experiments |
| **Solid Performance** | 500-1,000 | 3,500-7,000 | Good | Development, testing |
| **Production-Grade** | 1,000-5,000 | 7,000-35,000 | Excellent | User-facing systems |
| **Diminishing Returns** | 5,000+ | 35,000+ | Perfect | Marginal improvements |

### Class Imbalance Limits

| Ratio | Status | Action Required |
|-------|--------|-----------------|
| **1:3** | Ideal | Standard class weighting |
| **1:5** | Good | Class weighting |
| **1:10** | Concerning | Class weighting + monitoring |
| **1:50** | Critical | SMOTE + heavy weighting |
| **1:100+** | Extreme | Synthetic data + specialized methods |

---

## Quick Decision Tree

### "How much data do I need?"

```
START: What's your goal?
│
├─ Prove concept / Experiment
│  └─ 100-200 per class (700-1,400 total)
│     - Expect 70-80% accuracy
│     - High overfitting risk
│     - Max imbalance: 1:5
│
├─ Internal tool / Development
│  └─ 500-1,000 per class (3,500-7,000 total)
│     - Expect 85-92% accuracy
│     - Good generalization
│     - Max imbalance: 1:10
│
└─ Production / User-facing
   └─ 1,000-5,000 per class (7,000-35,000 total)
      - Expect 92-97% accuracy
      - Excellent generalization
      - Max imbalance: 1:3 to 1:5
```

### "Is my dataset balanced enough?"

```
Calculate: Majority Class Size ÷ Minority Class Size = Ratio

Ratio 1:1 to 1:3  → Perfect, no action needed
Ratio 1:3 to 1:5  → Good, standard class weighting
Ratio 1:5 to 1:10 → Concerning, class weighting + close monitoring
Ratio 1:10 to 1:100 → Critical, SMOTE + heavy class weighting required
Ratio > 1:100     → Extreme, collect more data or use synthetic generation
```

---

## Current Project Status

### Available Data
- **Current corpus:** 37,888 paragraphs, 7 classes
- **If balanced:** ~5,413 per class ✓ (production-grade range)
- **Expansion available:** ~800 PDFs ≈ 26,000 more paragraphs
- **Potential total:** ~64,000 paragraphs ≈ 9,143 per class

### Check Your Distribution

```bash
# Analyze current distribution
python scripts/corpus_building/build_clean_corpus.py --analyze
```

**Look for:**
1. Any class < 500 samples? 🔴 Critical - collect more data
2. Any class < 1,000 samples? 🟡 Concerning - monitor closely
3. Any class < 3,000 samples? 🟢 Adequate - optional expansion
4. Imbalance ratio > 1:10? 🔴 Requires intervention

---

## Rules of Thumb

### Transfer Learning Power
- **From scratch:** 5,000-10,000 samples per class
- **Pre-trained BERT:** 100-500 samples per class
- **Reduction factor:** 10-100x less data needed

### Sample Efficiency
- **True few-shot:** 10-40 samples (experimental only)
- **Performance plateau:** ~100 samples for many tasks
- **Diminishing returns:** Significant beyond 1,000 samples
- **Production minimum:** 1,000+ samples for robustness

### Training Efficiency
- **BERT epochs:** 2-4 epochs sufficient
- **ModernBERT:** 3x faster than BERT
- **Time to train:** Minutes to hours
- **ROI pattern:** Drops immediately after first epoch

---

## Class Weight Recommendations

### Standard Formula
```python
# Inverse frequency (scikit-learn "balanced")
class_weight = n_samples / (n_classes * n_samples_in_class)
```

### Manual Multipliers by Imbalance

| Imbalance Ratio | Minority Weight | Notes |
|-----------------|-----------------|-------|
| 1:3 | 1.5-2x | Slight boost |
| 1:5 | 2-3x | Moderate boost |
| 1:10 | 3-5x | Heavy boost |
| 1:50 | 10-20x | Very heavy + SMOTE |
| 1:100+ | 20-50x | Extreme + synthetic data |

**Current project:** Using 3x multiplier for body_text with good results (83.3% recall)

---

## When to Stop Collecting Data

### Stop if:
1. ✓ All classes > 1,000 samples
2. ✓ Imbalance ratio < 1:10
3. ✓ Validation accuracy plateaued
4. ✓ F1 scores > 90% for all classes
5. ✓ Production performance goals met

### Keep collecting if:
1. ✗ Any class < 500 samples
2. ✗ Imbalance ratio > 1:10
3. ✗ Validation accuracy still improving
4. ✗ Minority class F1 < 80%
5. ✗ Production accuracy < target

---

## Intervention Strategies by Scenario

### Scenario 1: Minority Class < 500 samples
**Priority:** CRITICAL
- [ ] Collect more real data (highest priority)
- [ ] Apply SMOTE or ADASYN
- [ ] Generate synthetic data (GPT, paraphrasing)
- [ ] Heavy class weighting (5-10x)
- [ ] Consider focal loss

### Scenario 2: Imbalance 1:10 to 1:50
**Priority:** HIGH
- [ ] Class weighting (3-10x minority)
- [ ] SMOTE in embedding space
- [ ] Threshold calibration
- [ ] Monitor minority class metrics closely
- [ ] Consider ensemble methods

### Scenario 3: All classes > 1,000, ratio < 1:10
**Priority:** LOW
- [ ] Standard class weighting (inverse frequency)
- [ ] Focus on model architecture
- [ ] Hyperparameter optimization
- [ ] Data quality over quantity

---

## Validation Checklist

Before proceeding to production:

- [ ] **Per-class counts:** All classes > 1,000 samples
- [ ] **Imbalance ratio:** < 1:10 (ideally < 1:5)
- [ ] **Data quality:** Manual spot-check 100 random samples
- [ ] **Diversity:** Multiple sources, layouts, styles represented
- [ ] **Validation set:** Stratified split, 10-20% of data
- [ ] **Class metrics:** F1 > 85% for all classes
- [ ] **Minority recall:** > 80% for all classes
- [ ] **Confusion matrix:** No systematic misclassifications

---

## Key Sources

### Academic
- JMIR AI (2024): "Sample Size Considerations for Fine-Tuning LLMs"
- OpenReview: "Revisiting Few-Sample BERT Fine-Tuning"
- arXiv 2409.03454: "How Much Data is Enough Data?"

### Benchmarks
- RVL-CDIP: 400K images, 25K per class (16 classes)
- DocLayNet: 80.8K pages (11 classes)
- LayoutLM: Fine-tuned on FUNSD (149 docs), CORD (800 docs)

### Industry
- UiPath: 20-50 samples/field (regular), 50-200 (columns)
- Azure: 500 pages (template), 50K pages (neural)
- Production: 1K-10K documents typical

---

## Emergency Triage

### 🔴 RED ALERT (Take Action Now)
- Any class < 100 samples
- Imbalance ratio > 1:100
- Minority class F1 < 50%
- **Action:** Stop training, collect more data

### 🟡 YELLOW WARNING (Monitor Closely)
- Any class 100-500 samples
- Imbalance ratio 1:10 to 1:100
- Minority class F1 50-70%
- **Action:** Apply SMOTE, heavy weighting, expand data

### 🟢 GREEN GO (Safe to Proceed)
- All classes > 1,000 samples
- Imbalance ratio < 1:10
- All class F1 > 80%
- **Action:** Focus on optimization, not data collection

---

**Quick Reference:** For full details and research sources, see `/docs/EMPIRICAL_DATA_SIZING_RESEARCH.md`
