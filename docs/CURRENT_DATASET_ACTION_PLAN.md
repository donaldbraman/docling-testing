# Current Dataset Action Plan

**Analysis Date:** October 16, 2025
**Corpus:** 8class_corpus.csv (42,205 samples, 7 classes)
**Status:** 🔴 CRITICAL - Immediate action required

---

## Executive Summary

**Current State:**
- Total samples: 42,205
- Imbalance ratio: 1:179.2 (body_text 22,761 vs page_footer 127)
- **4 critical classes** below 500 samples (caption, cover, page_footer, page_header)
- **2 production-ready classes** (body_text, footnote)

**Key Finding:** Extreme class imbalance (1:179) far exceeds research-backed safe threshold (1:10), requiring immediate intervention with SMOTE, synthetic data generation, and aggressive class weighting.

---

## Current Distribution

| Class | Count | % | Status | Imbalance vs Largest |
|-------|-------|---|--------|---------------------|
| **body_text** | 22,761 | 53.9% | ✅ Excellent | - |
| **footnote** | 16,687 | 39.5% | ✅ Excellent | 1:1.4 |
| **heading** | 1,518 | 3.6% | 🟢 Adequate | 1:15.0 |
| **cover** | 479 | 1.1% | 🔴 Critical | 1:47.5 |
| **page_header** | 389 | 0.9% | 🔴 Critical | 1:58.5 |
| **caption** | 244 | 0.6% | 🔴 Critical | 1:93.3 |
| **page_footer** | 127 | 0.3% | 🔴 Critical | 1:179.2 |

---

## Immediate Actions Required

### Priority 1: CRITICAL Classes (< 500 samples)

#### 1. page_footer (127 samples) - MOST CRITICAL
**Problem:** 1:179 imbalance, only 127 samples
**Target:** Minimum 500 samples (373 more needed)
**Actions:**
1. **Immediate:** Apply SMOTE to generate 373 synthetic samples in embedding space
2. **Short-term:** Collect real data from 800 available PDFs (prioritize cover pages)
3. **Model training:** Use 50x class weight (extreme intervention)
4. **Alternative:** Consider merging with page_header as "page_metadata" class

**Code:**
```python
# SMOTE in embedding space
from imblearn.over_sampling import SMOTE
# Generate to 500 samples minimum
smote = SMOTE(sampling_strategy={0: 500, 1: 500, ...}, random_state=42)
```

#### 2. caption (244 samples)
**Problem:** 1:93 imbalance, 244 samples
**Target:** Minimum 500 samples (256 more needed)
**Actions:**
1. **Immediate:** SMOTE to 500 samples
2. **Data collection:** Extract from figures in 800 available PDFs
3. **Model training:** 20-30x class weight
4. **Validation:** Manual review of SMOTE-generated samples for quality

#### 3. page_header (389 samples)
**Problem:** 1:59 imbalance, 389 samples
**Target:** Minimum 500 samples (111 more needed)
**Actions:**
1. **Immediate:** SMOTE to 500 samples
2. **Data collection:** Header extraction from PDFs (high success rate expected)
3. **Model training:** 15-20x class weight

#### 4. cover (479 samples)
**Problem:** 1:48 imbalance, 479 samples
**Target:** Minimum 500 samples (21 more needed)
**Actions:**
1. **Immediate:** SMOTE to 500 samples
2. **Data collection:** Cover page extraction (very easy to collect)
3. **Model training:** 10-15x class weight
4. **Note:** Closest to threshold, lowest priority

### Priority 2: Adequate Class (1,000-3,000 samples)

#### 5. heading (1,518 samples)
**Status:** Acceptable but could improve
**Target:** Maintain or expand to 2,000+
**Actions:**
1. **Current:** Use 3-5x class weight
2. **Optional:** SMOTE to 2,000 if expansion happens
3. **Monitor:** F1 score should be > 85%

### Priority 3: Production-Ready Classes

#### 6. body_text (22,761 samples) ✅
**Status:** Excellent, no action needed
**Current approach:** 3x class weight working well (83.3% recall)
**Note:** This is the most important class - maintain quality

#### 7. footnote (16,687 samples) ✅
**Status:** Excellent, no action needed
**Current approach:** Standard 1x weight sufficient

---

## Intervention Strategy

### Phase 1: Immediate (This Week)

**Goal:** Get all classes above 500 samples minimum

1. **Apply SMOTE to critical classes:**
   ```python
   # Target sampling strategy
   target_samples = {
       'page_footer': 500,
       'caption': 500,
       'page_header': 500,
       'cover': 500,
       'heading': 1518,  # Keep as is
       'body_text': 22761,  # Keep as is
       'footnote': 16687  # Keep as is
   }
   ```

2. **Update class weights for extreme imbalance:**
   ```python
   class_weight_multiplier = {
       'page_footer': 50.0,   # 1:179 ratio
       'caption': 30.0,       # 1:93 ratio
       'page_header': 20.0,   # 1:59 ratio
       'cover': 15.0,         # 1:48 ratio
       'heading': 5.0,        # 1:15 ratio
       'body_text': 1.0,      # Baseline
       'footnote': 1.0        # Baseline
   }
   ```

3. **Train with focal loss (alternative to class weights):**
   - Focuses learning on hard-to-classify examples
   - Better than pure class weighting for extreme imbalance
   - Helps prevent overfitting on synthetic data

### Phase 2: Short-Term (Next 2 Weeks)

**Goal:** Collect real data from 800 available PDFs

1. **Prioritize metadata extraction:**
   - page_footer: ~800 samples (1 per PDF)
   - page_header: ~800 samples (1 per PDF)
   - cover: ~800 samples (1 per PDF)
   - caption: ~200-400 samples (figures)

2. **Run collection pipeline:**
   ```bash
   # Process 800 PDFs prioritizing metadata
   python scripts/corpus_building/extract_metadata_classes.py \
     --focus page_footer,page_header,cover,caption \
     --pdf_dir data/raw_pdf/ \
     --output data/metadata_expansion.csv
   ```

3. **Validation:**
   - Manual review 10% of new samples (80 PDFs)
   - Check label quality, especially for captions
   - Ensure diverse sources (not all UCLA Law Review)

### Phase 3: Medium-Term (Next Month)

**Goal:** Achieve balanced dataset for production

1. **Target distribution:**
   - All classes: 1,000-5,000 samples
   - Imbalance ratio: < 1:10 (ideally 1:5)
   - Total: ~50,000-60,000 samples

2. **Projected after 800 PDF expansion + SMOTE:**
   ```
   body_text:    ~38,000 (60% of new data)
   footnote:     ~22,000 (20% of new data)
   heading:      ~2,500
   page_footer:  ~1,500 (w/ SMOTE + collection)
   page_header:  ~1,500 (w/ SMOTE + collection)
   caption:      ~1,300 (w/ SMOTE + collection)
   cover:        ~1,500 (w/ SMOTE + collection)

   Total: ~68,000 samples
   Imbalance: 1:25 (still concerning but much better)
   ```

3. **If still imbalanced (1:25):**
   - Continue with SMOTE for minorities
   - Consider undersampling body_text (not recommended, would lose data)
   - Use focal loss + class weighting combination

---

## Implementation Steps

### Step 1: SMOTE Implementation

Create `/Users/donaldbraman/Documents/GitHub/docling-testing/scripts/corpus_building/balance_corpus_smote.py`:

```python
import pandas as pd
from imblearn.over_sampling import SMOTE
from sklearn.preprocessing import LabelEncoder
import numpy as np

# Load corpus
df = pd.read_csv('data/8class_corpus.csv')

# Prepare features (use text embeddings from ModernBERT)
from transformers import AutoTokenizer, AutoModel
import torch

tokenizer = AutoTokenizer.from_pretrained('answerdotai/ModernBERT-base')
model = AutoModel.from_pretrained('answerdotai/ModernBERT-base')

# Get embeddings
embeddings = []
for text in df['text']:
    inputs = tokenizer(text, return_tensors='pt', truncation=True, max_length=512)
    with torch.no_grad():
        outputs = model(**inputs)
        embedding = outputs.last_hidden_state[:, 0, :].numpy()
    embeddings.append(embedding[0])

X = np.array(embeddings)
y = LabelEncoder().fit_transform(df['label'])

# Apply SMOTE
smote = SMOTE(
    sampling_strategy={
        0: 500,  # caption
        1: 500,  # cover
        2: max(500, df['label'].value_counts()['page_footer']),
        # ... etc
    },
    random_state=42
)

X_resampled, y_resampled = smote.fit_resample(X, y)

# Save resampled corpus
# ... (decode embeddings to text or save augmentation indices)
```

### Step 2: Update Training Script

Modify `/Users/donaldbraman/Documents/GitHub/docling-testing/scripts/training/train_multiclass_classifier.py`:

```python
# Add extreme class weights
class_weight_multiplier = {
    'page_footer': 50.0,
    'caption': 30.0,
    'page_header': 20.0,
    'cover': 15.0,
    'heading': 5.0,
    'body_text': 1.0,
    'footnote': 1.0
}

# Or use focal loss
from torchvision.ops import sigmoid_focal_loss

class FocalLoss(nn.Module):
    def __init__(self, alpha=0.25, gamma=2.0):
        super().__init__()
        self.alpha = alpha
        self.gamma = gamma

    def forward(self, inputs, targets):
        return sigmoid_focal_loss(inputs, targets, alpha=self.alpha, gamma=self.gamma)
```

### Step 3: Collect Metadata from PDFs

Create targeted extraction script:

```bash
python scripts/corpus_building/extract_metadata_priority.py \
  --classes page_footer,page_header,cover,caption \
  --min_samples 500 \
  --source_pdfs data/raw_pdf/ \
  --output data/metadata_balanced.csv
```

### Step 4: Validate and Combine

```python
# Combine SMOTE + real data
df_smote = pd.read_csv('data/smote_balanced.csv')
df_real = pd.read_csv('data/metadata_balanced.csv')
df_combined = pd.concat([df_smote, df_real]).drop_duplicates(subset=['text'])

# Validate distribution
print(df_combined['label'].value_counts())

# Check for leakage
from sklearn.model_selection import train_test_split
train, test = train_test_split(df_combined, test_size=0.2, stratify=df_combined['label'])
```

---

## Alternative Approaches

### Option 1: Class Merging (Reduce to 5 classes)
**Merge related classes to reduce imbalance:**
- Merge: page_footer + page_header → **page_metadata** (516 samples → still critical)
- Merge: cover + heading → **document_structure** (1,997 samples → adequate)
- Keep: body_text, footnote, caption

**Result:** 5 classes with better balance
**Trade-off:** Less granular classification

### Option 2: Hierarchical Classification
**Two-stage model:**
1. **Stage 1:** Binary - content vs metadata
2. **Stage 2:**
   - Content classifier: body_text, footnote, caption
   - Metadata classifier: heading, cover, page_header, page_footer

**Benefit:** Each classifier has better class balance
**Trade-off:** More complex pipeline

### Option 3: Focus on Critical Classes Only
**Train separate specialized models:**
- **Main model:** body_text, footnote, heading (well-balanced)
- **Metadata model:** page_header, page_footer, cover (collect more data)
- **Caption model:** Binary caption vs non-caption

**Benefit:** Each model optimized for its task
**Trade-off:** Inference requires multiple models

---

## Success Metrics

### Phase 1 Success (SMOTE + Weighting)
- [ ] All classes ≥ 500 samples (including synthetic)
- [ ] Model converges without class-specific failures
- [ ] Minority class recall ≥ 60% (improved from current)

### Phase 2 Success (Real Data Collection)
- [ ] Critical classes ≥ 1,000 samples (real + SMOTE)
- [ ] Imbalance ratio ≤ 1:50
- [ ] Minority class F1 ≥ 70%

### Phase 3 Success (Production Ready)
- [ ] All classes ≥ 1,000 samples (majority real data)
- [ ] Imbalance ratio ≤ 1:10 (ideally 1:5)
- [ ] All class F1 ≥ 85%
- [ ] Overall accuracy ≥ 95%

---

## Monitoring Plan

### Daily (During Phase 1)
- Training loss per class
- Confusion matrix showing per-class errors
- Synthetic vs real data performance gap

### Weekly (Phases 2-3)
- Data collection progress (target: 100+ PDFs/week)
- Class distribution evolution
- Model performance trends

### Before Production Deployment
- [ ] Inter-annotator agreement ≥ 90% on validation set
- [ ] Production test on 100 random real documents
- [ ] Edge case testing (unusual layouts, scanned PDFs)
- [ ] Performance comparison: SMOTE model vs real-data-only model

---

## Risk Assessment

### High Risk
1. **SMOTE overfitting:** Synthetic samples may not generalize
   - **Mitigation:** Validate on real data, use embedding-space SMOTE
   - **Fallback:** Collect more real data (800 PDFs available)

2. **Extreme class weights causing instability:** 50x weight may destabilize training
   - **Mitigation:** Gradual weight increase, focal loss as alternative
   - **Fallback:** Use hierarchical classification approach

### Medium Risk
3. **Data collection quality:** Automated extraction may introduce noise
   - **Mitigation:** Manual review 10% of new data
   - **Validation:** Cross-check with ground truth where available

4. **Imbalance persists after expansion:** Even 800 PDFs may not fully balance
   - **Mitigation:** Class merging or hierarchical approach
   - **Acceptance:** 1:25 ratio acceptable for production with focal loss

### Low Risk
5. **body_text performance degradation:** Heavy focus on minorities may hurt majority
   - **Monitoring:** Track body_text recall (target: maintain 80%+)
   - **Mitigation:** Separate validation set for body_text

---

## Timeline

### Week 1 (Current)
- [ ] Implement SMOTE balancing script
- [ ] Update training with extreme class weights
- [ ] Train model v3 with balanced synthetic data
- [ ] Evaluate performance on real validation set

### Week 2-3
- [ ] Begin PDF collection (target: 400 PDFs)
- [ ] Extract metadata priority classes
- [ ] Combine real + synthetic data
- [ ] Train model v4 with mixed data

### Week 4
- [ ] Complete PDF collection (remaining 400 PDFs)
- [ ] Validate all new data (manual review 80 samples)
- [ ] Train model v5 with expanded real data
- [ ] Performance comparison: v3 (synthetic) vs v5 (real+synthetic)

### Week 5-6
- [ ] Production validation testing
- [ ] Edge case evaluation
- [ ] Final model selection
- [ ] Documentation and deployment

---

## Next Steps (Immediate)

1. **Today:**
   - [ ] Review this plan with stakeholders
   - [ ] Decide: SMOTE approach vs class merging vs hierarchical
   - [ ] Create SMOTE implementation script

2. **This Week:**
   - [ ] Implement chosen balancing strategy
   - [ ] Train model v3 with balanced data
   - [ ] Evaluate on real validation set
   - [ ] Document results in issue #8 or new issue

3. **Next Week:**
   - [ ] Begin systematic PDF collection
   - [ ] Set up automated extraction pipeline
   - [ ] Establish validation workflow

---

**Priority Decision Needed:**
Which approach to pursue?
1. **SMOTE + Heavy Weighting** (fastest, but synthetic data risk)
2. **Class Merging** (reduces granularity, but improves balance)
3. **Hierarchical Classification** (more complex, but optimal balance)
4. **Combination:** SMOTE for immediate needs + real data collection for production

**Recommended:** Option 4 (Combination)
- Use SMOTE immediately to train model v3
- Collect real data in parallel
- Transition to real-data model (v5) for production
- Compare both to understand synthetic data impact

---

**Last Updated:** October 16, 2025
**Next Review:** October 23, 2025 (after SMOTE implementation)
