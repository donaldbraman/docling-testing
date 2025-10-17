# Data Sizing Research Summary

**Research Date:** October 16, 2025
**Project:** Document Structure Classification with ModernBERT
**Status:** 🔴 Critical imbalance detected - Action required

---

## Key Documents

1. **[EMPIRICAL_DATA_SIZING_RESEARCH.md](EMPIRICAL_DATA_SIZING_RESEARCH.md)** - Full research compilation with 50+ sources
2. **[DATA_SIZING_QUICK_REFERENCE.md](DATA_SIZING_QUICK_REFERENCE.md)** - Quick lookup tables and decision trees
3. **[CURRENT_DATASET_ACTION_PLAN.md](CURRENT_DATASET_ACTION_PLAN.md)** - Specific action plan for this project

---

## Research Findings in 60 Seconds

### Universal Thresholds (Transfer Learning with Pre-trained Transformers)

| Tier | Per Class | Total (7 classes) | Expected Accuracy | Use Case |
|------|-----------|-------------------|-------------------|----------|
| **Minimum Viable** | 100-500 | 700-3,500 | 70-80% | Proof of concept |
| **Solid Performance** | 500-1,000 | 3,500-7,000 | 85-92% | Development |
| **Production-Grade** | 1,000-5,000 | 7,000-35,000 | 92-97% | User-facing |
| **Diminishing Returns** | 5,000+ | 35,000+ | <1% gain | Marginal improvement |

### Class Imbalance Tolerance

| Ratio | Status | Action |
|-------|--------|--------|
| 1:3 | ✅ Ideal | Standard weighting |
| 1:5 | 🟢 Good | Class weighting |
| 1:10 | 🟡 Concerning | SMOTE + weighting |
| 1:50 | 🔴 Critical | Heavy intervention |
| 1:100+ | 🔴 Extreme | Synthetic data required |

---

## Our Project Status

### Current Corpus Analysis
**File:** `data/8class_corpus.csv`
**Total:** 42,205 samples across 7 classes

| Class | Count | % | Status | Imbalance |
|-------|-------|---|--------|-----------|
| body_text | 22,761 | 53.9% | ✅ Excellent | - |
| footnote | 16,687 | 39.5% | ✅ Excellent | 1:1.4 |
| heading | 1,518 | 3.6% | 🟢 Adequate | 1:15 |
| cover | 479 | 1.1% | 🔴 Critical | 1:48 |
| page_header | 389 | 0.9% | 🔴 Critical | 1:59 |
| caption | 244 | 0.6% | 🔴 Critical | 1:93 |
| page_footer | 127 | 0.3% | 🔴 Critical | 1:179 |

**Overall Imbalance:** 1:179 🔴 (FAR exceeds safe 1:10 threshold)

### Critical Issues

1. **4 classes below 500 samples** (caption, cover, page_footer, page_header)
2. **Extreme imbalance** (1:179 ratio vs research-backed 1:10 limit)
3. **page_footer most critical:** Only 127 samples, 1:179 imbalance

---

## Immediate Recommendations

### Phase 1: This Week (SMOTE + Weighting)
**Goal:** Get all classes above 500 samples using synthetic data

```python
# Apply SMOTE to bring critical classes to 500 minimum
target_samples = {
    'page_footer': 500,   # +373 synthetic
    'caption': 500,       # +256 synthetic
    'page_header': 500,   # +111 synthetic
    'cover': 500          # +21 synthetic
}

# Extreme class weights for 1:179 imbalance
class_weights = {
    'page_footer': 50.0,
    'caption': 30.0,
    'page_header': 20.0,
    'cover': 15.0,
    'heading': 5.0,
    'body_text': 1.0,
    'footnote': 1.0
}
```

### Phase 2: Next 2 Weeks (Real Data Collection)
**Goal:** Collect real data from 800 available PDFs

**Expected gains:**
- page_footer: +800 samples → 927 total
- page_header: +800 samples → 1,189 total
- cover: +800 samples → 1,279 total
- caption: +200 samples → 444 total (still critical)

### Phase 3: Next Month (Production Dataset)
**Goal:** Achieve 1:10 or better imbalance ratio

**Target distribution:**
- All classes: 1,000-5,000 samples
- Imbalance: < 1:10 (ideally 1:5)
- Method: Real data + balanced SMOTE

---

## Key Research Insights

### 1. Transfer Learning Power
- **From scratch:** Need 5,000-10,000 samples per class
- **Pre-trained BERT:** Only 100-500 samples per class
- **Reduction factor:** 10-100x less data with transfer learning

### 2. Diminishing Returns
- **Performance plateaus** around 100 samples for many tasks
- **Significant gains** up to 1,000 samples
- **Marginal improvement** beyond 5,000 samples
- **ROI drops immediately** after first epoch of fine-tuning

### 3. Class Imbalance Science
- **1:10 ratio** is common threshold for requiring intervention
- **Beyond 1:100** approaches often fail without synthetic data
- **Minority class performance** drops to 0-10% accuracy at extreme ratios
- **SMOTE in embedding space** more effective than feature-space SMOTE

### 4. Document AI Benchmarks
- **RVL-CDIP:** 25,000 samples per class (perfectly balanced)
- **DocLayNet:** 80,863 pages for 11 classes
- **LayoutLM fine-tuning:** Successful with 149-800 documents
- **UiPath guidelines:** 20-50 samples per field minimum

### 5. Production Best Practices
- **Data quality > quantity** beyond minimum thresholds
- **Diverse sources** prevent overfitting to single layout type
- **Manual validation** of 10% recommended
- **Stratified splits** essential for imbalanced data

---

## Alternative Strategies

### Option 1: Class Merging
**Reduce to 5 classes:**
- `page_metadata` = page_footer + page_header (516 samples)
- `document_structure` = cover + heading (1,997 samples)
- Keep: body_text, footnote, caption

**Pro:** Better balance immediately
**Con:** Less granular classification

### Option 2: Hierarchical Classification
**Two-stage approach:**
1. **Stage 1:** content vs metadata (binary)
2. **Stage 2a:** body_text, footnote, caption
3. **Stage 2b:** heading, cover, page_header, page_footer

**Pro:** Each classifier well-balanced
**Con:** More complex pipeline

### Option 3: Focal Loss
**Instead of extreme class weights:**
```python
# Focal Loss focuses on hard examples
focal_loss = FocalLoss(alpha=0.25, gamma=2.0)
# Automatically handles imbalance
```

**Pro:** More stable than 50x class weights
**Con:** Requires custom loss implementation

---

## Success Criteria

### Short-term (This Week)
- [ ] All classes ≥ 500 samples (SMOTE)
- [ ] Model converges without failures
- [ ] Minority class recall ≥ 60%

### Medium-term (This Month)
- [ ] Critical classes ≥ 1,000 samples (real data)
- [ ] Imbalance ratio ≤ 1:50
- [ ] All class F1 ≥ 70%

### Long-term (Production)
- [ ] All classes ≥ 1,000 samples
- [ ] Imbalance ratio ≤ 1:10
- [ ] All class F1 ≥ 85%
- [ ] Overall accuracy ≥ 95%

---

## Data Collection Roadmap

### Available Resources
- **800 additional PDFs** in pipeline
- **~26,000 estimated paragraphs**
- **Focus areas:** Law reviews, legal documents

### Projected After Expansion

| Class | Current | After SMOTE | After Collection | Final Target |
|-------|---------|-------------|------------------|--------------|
| page_footer | 127 | 500 | 1,500 | ✅ |
| caption | 244 | 500 | 700 | 🟡 Still below 1K |
| page_header | 389 | 500 | 1,500 | ✅ |
| cover | 479 | 500 | 1,500 | ✅ |
| heading | 1,518 | 1,518 | 2,500 | ✅ |
| footnote | 16,687 | 16,687 | 22,000 | ✅ |
| body_text | 22,761 | 22,761 | 38,000 | ✅ |

**Note:** Caption still concerning - may need targeted collection or SMOTE

---

## Academic Sources (Selected)

1. **JMIR AI (2024):** "Sample Size Considerations for Fine-Tuning LLMs"
   - Finding: "Relatively modest sample sizes" sufficient for NER
   - Emphasis on quality over quantity

2. **OpenReview:** "Revisiting Few-Sample BERT Fine-Tuning"
   - Minimum: 1,000 examples per task
   - Few-shot: 100 samples can work with caveats

3. **arXiv 2409.03454:** "How Much Data is Enough?"
   - Translation tasks: deterioration with 1-2K samples
   - Substantial improvement beyond 5K

4. **DocLayNet (KDD 2022):** Document layout dataset
   - 80,863 pages, 11 classes
   - Production annotation: 3 months, 32 annotators

5. **UiPath Documentation:** Document Understanding
   - Regular fields: 20-50 samples minimum
   - Column fields: 50-200 samples minimum

---

## Tools and Scripts

### Analysis
```bash
# Check current distribution
python scripts/corpus_building/build_clean_corpus.py --analyze

# Visualize class imbalance
python scripts/analysis/plot_class_distribution.py
```

### Balancing
```bash
# Apply SMOTE (to be created)
python scripts/corpus_building/balance_corpus_smote.py \
  --input data/8class_corpus.csv \
  --output data/balanced_corpus.csv \
  --strategy critical  # Only balance classes < 500

# Extract metadata priority
python scripts/corpus_building/extract_metadata_priority.py \
  --focus page_footer,page_header,cover,caption \
  --min_samples 500
```

### Training
```bash
# Train with extreme class weights
python scripts/training/train_multiclass_classifier.py \
  --corpus data/balanced_corpus.csv \
  --class_weights extreme \
  --epochs 100 \
  --output models/doclingbert-v3-balanced/
```

---

## Decision Point

**Choose your approach:**

### A. Conservative (Recommended)
1. SMOTE to get critical classes to 500
2. Collect real data from 800 PDFs
3. Retrain with real+synthetic mix
4. Validate on real data only

**Timeline:** 3-4 weeks
**Risk:** Low
**Quality:** High (majority real data)

### B. Aggressive (Faster)
1. Heavy SMOTE to 1,000 per class
2. Train immediately with 20-50x weights
3. Collect real data in parallel
4. Compare synthetic vs real performance

**Timeline:** 1-2 weeks
**Risk:** Medium (overfitting to synthetic)
**Quality:** Medium-High

### C. Hybrid (Balanced)
1. SMOTE critical classes to 500
2. Class merging for severe imbalances
3. Hierarchical model for metadata
4. Targeted real data collection

**Timeline:** 2-3 weeks
**Risk:** Low-Medium
**Quality:** High

---

## Next Steps

1. **Review research findings** with team
2. **Choose balancing strategy** (A, B, or C)
3. **Create SMOTE implementation** script
4. **Set up data collection** pipeline for 800 PDFs
5. **Monitor minority class metrics** closely

---

## Quick Links

- **Full Research:** [EMPIRICAL_DATA_SIZING_RESEARCH.md](EMPIRICAL_DATA_SIZING_RESEARCH.md)
- **Quick Reference:** [DATA_SIZING_QUICK_REFERENCE.md](DATA_SIZING_QUICK_REFERENCE.md)
- **Action Plan:** [CURRENT_DATASET_ACTION_PLAN.md](CURRENT_DATASET_ACTION_PLAN.md)
- **Current Model:** `models/doclingbert-v2-rebalanced/`
- **Issue Tracker:** [GitHub Issue #8](https://github.com/donaldbraman/docling-testing/issues/8)

---

**Bottom Line:**
- ✅ We have **excellent** data for body_text and footnote (>15K samples each)
- 🟢 We have **adequate** data for heading (1,518 samples)
- 🔴 We have **critical shortage** for page_footer, caption, page_header, cover (<500 samples)
- 🔴 Our **1:179 imbalance** far exceeds safe 1:10 research threshold
- 🎯 **Action:** Apply SMOTE immediately + collect 800 PDFs for real data

**Recommended:** Start with Conservative approach (A) - SMOTE to 500 + real data collection

---

**Last Updated:** October 16, 2025
**Next Review:** After SMOTE implementation and initial model v3 training
