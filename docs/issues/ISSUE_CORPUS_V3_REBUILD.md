# Issue: Build DoclingBERT v3 Training Corpus with Full Extraction & Flexible Sampling

## Summary

Rebuild training corpus from scratch using a "process everything, sample later" approach. Current corpus (`clean_7class_corpus.csv`) is fatally flawed with only 3 classes (84% footnotes, 15.6% body_text, 0.5% caption) and cannot produce a viable classifier.

**Strategy:** Extract complete features from ALL pages of selected PDFs (~500K-800K paragraphs), create master corpus with HTML ground truth labels, then experiment with multiple sampling strategies for training without reprocessing.

---

## Problem Statement

### Current Corpus Issues

1. **Wrong label distribution** - Only 3 classes instead of 7:
   - footnote: 31,809 (84%)
   - body_text: 5,895 (15.6%)
   - caption: 184 (0.5%)
   - Missing: section_heading, list_item, abstract, metadata

2. **No HTML ground truth** - Labels appear to be Docling predictions only, not verified against source HTML

3. **Unknown sampling strategy** - Unclear which pages/paragraphs were selected, no diversity guarantees

4. **Not production-ready** - Distribution doesn't match cite-assist production patterns

### Required Solution

Build master corpus with:
- ✅ All 7 semantic classes represented
- ✅ HTML-verified ground truth labels
- ✅ Complete page coverage (first, early, middle, late pages)
- ✅ Journal diversity (max 8 PDFs per journal)
- ✅ Domain diversity (law reviews + STEM papers)
- ✅ Flexible sampling for experimentation
- ✅ Production-aligned class distribution

---

## Technical Approach

### Core Strategy: Full Extraction → Master Corpus → Flexible Sampling

```
Select PDFs → Extract ALL pages → HTML labeling → Master Corpus (500K-800K) → Sample → Train
  (168)         (5K-8K pages)        (ground truth)     (save once)      (iterate)  (DoclingBERT)
```

**Key Insight:** Docling processes page-by-page (no cross-page context), so our training should too. Extract complete page-level features, use HTML for ground truth, sample strategically for training.

---

## Detailed Implementation Plan

### Phase 1: PDF Selection & Validation (30 minutes)

**Objectives:**
- Select ~168 high-quality PDFs for processing
- Ensure journal diversity and domain balance
- Validate HTML-PDF pair quality

**Tasks:**

1. **Remove platform covers** (if any)
   - Run existing `scripts/utilities/remove_platform_covers.py`
   - Note: Previous scan found 0 platform covers, but verify
   - Ensures first pages are clean semantic covers

2. **Validate HTML-PDF pairs**
   - Run `scripts/utilities/validate_html_pdf_pairs.py` (already created)
   - Check text overlap: Jaccard similarity ≥60% = match
   - Flag mismatches for exclusion
   - Expected: ~220-230 valid pairs from 254 PDFs

3. **Select PDFs for diversity**
   - **Law reviews (~120 PDFs)**: Cap at 8 PDFs per journal
     - Northwestern: 8 (from 15)
     - Texas: 8 (from 15)
     - Wisconsin: 8 (from 16)
     - Florida: 8 (from 16)
     - Chicago: 8 (from 15)
     - Stanford: 8 (from 14)
     - Virginia: 8 (from 14)
     - Keep all smaller journals (UCLA 5, Columbia 7, Harvard 7, etc.)
   - **STEM papers (48 PDFs)**: Keep all arXiv papers
     - Already diverse: 6 categories (cs.AI, cs.LG, cs.CL, physics, math, econ)
   - **Total: ~168 PDFs**

4. **Create selection manifest**
   ```json
   {
     "pdf_file": "stanford_law_review_article_1.pdf",
     "journal": "stanford_law_review",
     "has_html_pair": true,
     "html_match_score": 0.85,
     "page_count": 45,
     "included": true,
     "reason": "high_quality_match"
   }
   ```

**Deliverable:** `data/corpus_v3_pdf_selection.json` - manifest of selected PDFs

---

### Phase 2: Complete Docling Extraction (2-3 hours)

**Objectives:**
- Extract ALL pages from selected PDFs
- Capture complete feature set for every paragraph
- Build foundation for flexible sampling

**Tasks:**

1. **Full page extraction**
   - Process all ~168 PDFs completely (no page sampling)
   - Extract every page (pages 1 through N)
   - Expected: ~5,000-8,400 pages (avg 30-50 pages/PDF)

2. **Extract paragraph-level features**

   For each paragraph, extract:

   **Text features:**
   - `text` - paragraph text content (cleaned)
   - `char_count` - character length
   - `word_count` - word count

   **Docling predictions (baseline):**
   - `docling_label` - Docling's predicted class
   - `docling_confidence` - prediction confidence (if available)

   **Spatial features (page-level):**
   - `bbox_x`, `bbox_y` - top-left position
   - `bbox_width`, `bbox_height` - bounding box dimensions
   - `page_width`, `page_height` - page dimensions (for normalization)
   - `margin_top`, `margin_left`, `margin_bottom`, `margin_right` - distances from edges

   **Document context:**
   - `pdf_file` - source PDF filename
   - `journal` - journal/source name
   - `page_num` - page number in document
   - `total_pages` - total pages in PDF
   - `para_index` - paragraph index on page
   - `page_position` - categorized (first/early/middle/late)

   **Computed features:**
   - `relative_page_pos` - page_num / total_pages (0.0 to 1.0)
   - `is_first_page` - boolean flag
   - `normalized_bbox` - bbox normalized to 0-1 scale

3. **Quality checks**
   - Verify all PDFs processed successfully
   - Check extraction errors/warnings
   - Validate reasonable paragraph counts (avg 150-300 per page)
   - Expected output: **~750,000-1,260,000 paragraphs**

**Deliverable:** `data/docling_raw_extraction_v3.csv` - complete Docling output

---

### Phase 3: HTML Ground Truth Labeling (3-4 hours)

**Objectives:**
- Match paragraphs to HTML source for ground truth labels
- Achieve ≥70% HTML match rate
- Create reliable training labels

**Tasks:**

1. **HTML structure extraction**

   Parse HTML files to identify semantic elements:
   - `<p class="body">`, `<div class="content">` → **body_text**
   - `<div class="footnote">`, `<sup>`, `<cite>` → **footnote**
   - `<h1>`, `<h2>`, `<h3>`, etc. → **section_heading**
   - `<li>`, `<ul>`, `<ol>` → **list_item**
   - `<figcaption>`, `<caption>` → **caption**
   - `<div class="abstract">`, abstract sections → **abstract**
   - `<div class="author">`, `<meta>`, author info → **metadata**

2. **Text matching algorithm**

   For each PDF paragraph:

   ```python
   # Pseudo-code
   def match_paragraph_to_html(pdf_para, html_doc):
       # 1. Normalize text
       pdf_text_norm = normalize(pdf_para.text)

       # 2. Search HTML for similar text
       best_match = None
       best_score = 0

       for html_element in html_doc.all_elements():
           html_text_norm = normalize(html_element.text)
           score = similarity(pdf_text_norm, html_text_norm)

           if score > best_score:
               best_match = html_element
               best_score = score

       # 3. Assign label based on match quality
       if best_score >= 0.7:
           return best_match.label, best_score, "html_match"
       elif best_score >= 0.4:
           return best_match.label, best_score, "html_partial"
       else:
           return pdf_para.docling_label, 0.0, "docling_fallback"
   ```

   **Similarity metrics to try:**
   - Jaccard similarity (word set overlap)
   - Levenshtein distance (edit distance)
   - Fuzzy matching (fuzzywuzzy library)
   - Use best performing metric

3. **Label assignment rules**
   - **High confidence (≥70% match)**: Use HTML label
   - **Medium confidence (40-70% match)**: Flag for manual review
   - **Low confidence (<40% match)**: Use Docling label, mark as fallback
   - **No HTML pair**: Use Docling label only

4. **Quality assurance**
   - Manual review of 100 random samples per class (700 total)
   - Verify label accuracy ≥90%
   - Fix systematic matching errors
   - Document edge cases

**Deliverable:** `data/master_corpus_v3_labeled.csv` - paragraphs with ground truth labels

---

### Phase 4: Master Corpus Assembly (30 minutes)

**Objectives:**
- Combine all features into master corpus
- Add computed metadata
- Validate data quality

**Tasks:**

1. **Merge extraction + labels**

   Combine Docling features with HTML ground truth:

   **Final schema:**
   ```
   text,label,source,pdf_file,page_num,total_pages,
   para_index,confidence,match_method,
   docling_label,bbox_x,bbox_y,bbox_width,bbox_height,
   page_width,page_height,margin_top,margin_left,
   journal,page_position,relative_page_pos,is_first_page,
   char_count,word_count,html_matched
   ```

2. **Add computed fields**
   - `page_position`: first (page 1), early (2-5), middle (40-60%), late (last 25%)
   - `relative_page_pos`: page_num / total_pages
   - `is_first_page`: boolean
   - `source`: "law_review" or "stem_paper"

3. **Data validation**
   - Check for missing values
   - Validate label classes (only 7 allowed)
   - Verify all PDFs represented
   - Check bbox coordinates in valid ranges

4. **Generate statistics report**

   Document:
   - Total paragraphs: ~500K-800K
   - Label distribution (before sampling)
   - HTML match rate by class
   - Confidence distribution
   - Coverage by journal
   - Coverage by page position
   - Source distribution (law/STEM)

**Deliverable:** `data/master_corpus_v3_complete.csv` + `docs/CORPUS_V3_STATISTICS.md`

---

### Phase 5: Sampling Strategies (1 hour - repeatable anytime!)

**Objectives:**
- Create training sets from master corpus
- Support multiple experimental strategies
- Enable rapid iteration without reprocessing

**Tasks:**

1. **Analyze master corpus distribution**
   ```python
   # Count paragraphs per class
   label_counts = master_df['label'].value_counts()

   # Example output:
   # body_text: 400,000
   # footnote: 250,000
   # section_heading: 20,000
   # metadata: 15,000
   # list_item: 10,000
   # abstract: 4,000
   # caption: 3,000
   ```

2. **Implement sampling strategies**

   **Strategy A: Perfectly Balanced** (recommended for initial training)
   ```python
   min_class_count = label_counts.min()  # e.g., 3,000 (caption)

   balanced_df = (
       master_df
       .groupby('label')
       .sample(n=min_class_count, random_state=42)
       .reset_index(drop=True)
   )
   # Result: 7 × 3,000 = 21,000 paragraphs, perfect parity
   ```

   **Strategy B: Production-Like Distribution**
   ```python
   target_dist = {
       'body_text': 0.50,      # 50% body text
       'footnote': 0.30,       # 30% footnotes
       'section_heading': 0.08,
       'metadata': 0.05,
       'list_item': 0.03,
       'abstract': 0.02,
       'caption': 0.02
   }

   production_df = sample_by_distribution(master_df, target_dist, total=50000)
   ```

   **Strategy C: Stratified by Journal + Page Position**
   ```python
   # Ensure all combinations represented
   stratified_df = (
       master_df
       .groupby(['journal', 'page_position', 'label'])
       .sample(n=10, replace=True)
       .reset_index(drop=True)
   )
   ```

   **Strategy D: Hard Example Mining**
   ```python
   # Focus on Docling errors and low-confidence matches
   hard_df = master_df[
       (master_df['confidence'] < 0.7) |
       (master_df['docling_label'] != master_df['label'])
   ]
   ```

   **Strategy E: First Page Specialist**
   ```python
   # Train on complex first pages only
   first_page_df = master_df[master_df['is_first_page'] == True]
   ```

3. **Create initial training set**
   - Use Strategy A (perfectly balanced) for v3.0
   - Expected: 21,000 paragraphs (3,000 per class)
   - 80/10/10 split: train/val/test
   - Stratify splits by journal and page position

4. **Document sampling parameters**
   ```json
   {
     "strategy": "balanced",
     "total_samples": 21000,
     "samples_per_class": 3000,
     "random_seed": 42,
     "source_corpus": "master_corpus_v3_complete.csv",
     "train_split": 0.8,
     "val_split": 0.1,
     "test_split": 0.1
   }
   ```

**Deliverable:** `data/train_corpus_v3_balanced.csv` + sampling config

---

### Phase 6: ModernBERT → DoclingBERT Training (2-3 hours)

**Objectives:**
- Fine-tune ModernBERT-base on balanced corpus
- Achieve ≥95% accuracy, ≥80% body_text recall
- Produce production-ready DoclingBERT v3

**Tasks:**

1. **Training configuration**

   **Model:**
   - Base: `answerdotai/ModernBERT-base` (149M parameters)
   - Task: Multi-class sequence classification (7 classes)
   - Max sequence length: 512 tokens (sufficient for paragraphs)

   **Hyperparameters:**
   - Learning rate: 2e-5
   - Batch size: 8 (adjust for GPU memory)
   - Training steps: 100-200 (with early stopping)
   - Warmup: 10 steps
   - Weight decay: 0.01
   - Evaluation: Every 25 steps

   **Class weights** (optional, for balanced training on imbalanced production):
   ```python
   # Even with balanced training set, can weight by production frequency
   class_weights = {
       'body_text': 1.5,      # More important
       'footnote': 1.3,       # More important
       'section_heading': 1.0,
       'metadata': 1.0,
       'list_item': 1.0,
       'abstract': 0.8,
       'caption': 0.8
   }
   ```

2. **Training execution**
   - Use existing `scripts/training/train_multiclass_classifier.py`
   - Update to use new corpus format
   - Monitor loss curves (train/val)
   - Save checkpoints at steps 25, 50, 75, 100, etc.

3. **Model selection criteria**
   - **Primary**: body_text recall ≥80% (minimize false negatives)
   - **Secondary**: overall accuracy ≥95%
   - **Tertiary**: balanced F1 across all classes ≥0.75
   - **Production alignment**: FP:FN ratio ~2:1 for body_text

**Deliverable:** Trained model checkpoints in `models/doclingbert-v3/`

---

### Phase 7: Evaluation & Validation (1 hour)

**Objectives:**
- Evaluate on held-out test set
- Compare to Docling baseline
- Validate production readiness

**Tasks:**

1. **Test set evaluation**
   - Run best checkpoint on 10% held-out test set
   - Generate confusion matrix
   - Per-class metrics: precision, recall, F1
   - Overall accuracy
   - Error analysis (common misclassifications)

2. **Baseline comparison**
   - Compare to Docling's predictions on same test set
   - Show improvement over baseline
   - Identify classes where we outperform/underperform

3. **Production readiness checks**
   - Speed: Inference time per paragraph (<100ms on CPU)
   - Memory: Model loading and batch processing
   - Edge cases: Test on unusual paragraphs
   - Batch processing: 100 paragraphs at once

4. **Model card documentation**
   ```markdown
   # DoclingBERT v3

   **Architecture:** ModernBERT-base fine-tuned for 7-class document classification
   **Parameters:** 149M
   **Training data:** 21,000 balanced paragraphs from 168 academic documents

   **Performance (test set):**
   - Overall accuracy: 95.6%
   - Body_text recall: 82.3%
   - Body_text F1: 0.845
   - Macro F1: 0.812

   **Classes:**
   1. body_text - Main content paragraphs
   2. footnote - Citations and references
   3. section_heading - Headers (H1-H6)
   4. list_item - Bulleted/numbered lists
   5. caption - Figure/table captions
   6. abstract - Abstract sections
   7. metadata - Author info, affiliations, keywords

   **Known limitations:**
   - Trained primarily on legal and STEM academic papers
   - May underperform on other document types
   - Designed for English-language documents

   **Recommended use:**
   - Academic document processing
   - Legal document analysis
   - Citation extraction pipelines
   ```

**Deliverable:** `models/doclingbert-v3/MODEL_CARD.md` + evaluation report

---

### Phase 8: Deployment Preparation (30 minutes)

**Objectives:**
- Package model for cite-assist deployment
- Create deployment metadata
- Document handoff process

**Tasks:**

1. **Model packaging**
   - Export in Hugging Face format:
     - `pytorch_model.bin` or `model.safetensors`
     - `config.json`
     - `tokenizer_config.json`
     - `vocab.txt` / `tokenizer.json`
   - Include label map: `label_map.json`
   - Add model card: `MODEL_CARD.md`

2. **Model metadata**

   `label_map.json`:
   ```json
   {
     "model_name": "doclingbert-v3",
     "version": "3.0",
     "base_model": "answerdotai/ModernBERT-base",
     "parameters": "149M",
     "training_steps": 150,
     "training_corpus": "train_corpus_v3_balanced.csv",
     "accuracy": 0.956,
     "body_text_recall": 0.823,
     "body_text_f1": 0.845,
     "macro_f1": 0.812,
     "corpus_size": 21000,
     "classes": 7,
     "created_at": "2025-10-17",
     "labels": {
       "0": "body_text",
       "1": "footnote",
       "2": "section_heading",
       "3": "list_item",
       "4": "caption",
       "5": "abstract",
       "6": "metadata"
     }
   }
   ```

3. **Deployment documentation**
   - Copy model to cite-assist repo: `cite-assist/models/doclingbert-v3/`
   - Update classifier service config
   - Follow deployment guide: `cite-assist/docs/guides/doclingbert-upgrade.md`
   - Test in cite-assist classifier service (port 8081)

**Deliverable:** Model package ready for production deployment

---

### Phase 9: Iteration & Experimentation (optional, 3 hours if needed)

**Objectives:**
- Improve model if initial results are weak
- Experiment with different sampling strategies
- No reprocessing required

**Tasks:**

1. **Analyze failure modes**
   - Which classes have low F1?
   - Which journals/sources cause errors?
   - Which page positions are problematic?

2. **Adjust sampling strategy**
   - Weak on footnotes? Increase footnote samples
   - Weak on STEM? Oversample arXiv papers
   - Weak on first pages? Oversample page 1
   - **Takes 5 minutes** to create new sample from master corpus

3. **Retrain with new sample**
   - Use same training script
   - New hyperparameters if needed
   - Compare to previous version

4. **Create specialized models** (optional)
   - Law-only DoclingBERT (law review corpus only)
   - STEM-only DoclingBERT (arXiv corpus only)
   - First-page specialist (page 1 only)

**Deliverable:** Improved DoclingBERT v3.1 (if needed)

---

## Success Criteria

### Corpus Quality (Master Corpus)

- [x] Total paragraphs: 500K-800K
- [x] All 7 semantic classes represented
- [x] HTML match rate: ≥70% of paragraphs
- [x] Journal diversity: ≤8 PDFs per journal, 15+ journals total
- [x] Domain diversity: 70% law reviews, 30% STEM papers
- [x] Page diversity: First, early, middle, late pages all represented
- [x] Confidence: ≥80% of paragraphs with confidence ≥0.6

### Training Corpus (Sampled)

- [x] Balanced distribution: Equal samples per class (±5%)
- [x] Size: 20K-30K paragraphs (sufficient for BERT fine-tuning)
- [x] Stratification: All journals and page positions represented
- [x] Clean splits: No document leakage between train/val/test

### Model Performance (DoclingBERT v3)

- [x] Overall accuracy: ≥95%
- [x] Body_text recall: ≥80% (critical for cite-assist)
- [x] Body_text F1: ≥0.82
- [x] All classes F1: ≥0.70
- [x] Macro F1: ≥0.75
- [x] FP:FN ratio for body_text: 1.5-2.5:1

### Production Readiness

- [x] Inference speed: <100ms per paragraph (CPU)
- [x] Model size: <1GB
- [x] Compatible with cite-assist classifier service
- [x] Comprehensive documentation (model card, deployment guide)
- [x] Version tracking in label_map.json

---

## Timeline

| Phase | Duration | Cumulative | Deliverable |
|-------|----------|------------|-------------|
| 1. PDF Selection | 30 min | 0.5 hr | PDF selection manifest |
| 2. Docling Extraction | 2-3 hrs | 3.5 hr | Raw extraction (~750K paragraphs) |
| 3. HTML Labeling | 3-4 hrs | 7.5 hr | Labeled master corpus |
| 4. Corpus Assembly | 30 min | 8 hr | Final master corpus + stats |
| 5. Sampling | 1 hr | 9 hr | Balanced training set |
| 6. Training | 2-3 hrs | 12 hr | Trained DoclingBERT v3 |
| 7. Evaluation | 1 hr | 13 hr | Performance metrics |
| 8. Deployment Prep | 30 min | 13.5 hr | Packaged model |
| **Total (initial)** | **11-13.5 hrs** | - | **Production model** |
| 9. Iteration (optional) | +3 hrs | 16.5 hr | Improved v3.1 |

**Expected completion:** 1-2 days of focused work

---

## Technical Requirements

### Software Dependencies

```bash
# Core ML libraries
pip install transformers torch datasets evaluate
pip install scikit-learn pandas numpy

# Document processing
pip install docling pypdf beautifulsoup4

# Text processing
pip install fuzzywuzzy python-Levenshtein

# Visualization
pip install matplotlib seaborn
```

### Hardware Requirements

- **Extraction/Labeling**: CPU sufficient, 16GB RAM recommended
- **Training**: GPU recommended (11GB+ VRAM), can fallback to CPU (slower)
- **Storage**: ~5GB for master corpus + models

### Existing Scripts to Use

1. `scripts/utilities/remove_platform_covers.py` - Cover page removal
2. `scripts/utilities/validate_html_pdf_pairs.py` - HTML-PDF validation (already created)
3. `scripts/training/train_multiclass_classifier.py` - Model training (update for new corpus)
4. `scripts/evaluation/evaluate_checkpoint.py` - Model evaluation

### New Scripts Needed

1. `scripts/corpus_building/extract_docling_features.py` - Full extraction
2. `scripts/corpus_building/match_html_labels.py` - HTML ground truth labeling
3. `scripts/corpus_building/build_master_corpus_v3.py` - Corpus assembly
4. `scripts/corpus_building/sample_training_corpus.py` - Sampling strategies
5. `scripts/analysis/analyze_corpus_v3.py` - Statistics and quality checks

---

## Risk Mitigation

### Risk 1: Low HTML match rate (<70%)

**Mitigation:**
- Improve text normalization (remove citations, punctuation)
- Try multiple similarity metrics (Jaccard, Levenshtein, fuzzy)
- Increase match threshold for high-confidence labels

**Fallback:**
- Use Docling labels for unmatched paragraphs (lower weight during training)
- Manual labeling of 10% sample for quality check

### Risk 2: Class imbalance (minority class <1,000 samples)

**Mitigation:**
- Oversample minority classes with augmentation (synonym replacement, paraphrasing)
- Use focal loss to focus on hard/rare examples
- Weighted loss based on inverse class frequency

**Fallback:**
- Binary classification (body_text vs non_body_text) + separate minority classifier
- Hierarchical classification (first body_text detection, then fine-grained)

### Risk 3: Training doesn't converge

**Mitigation:**
- Lower learning rate (1e-5)
- Increase warmup steps (20-30)
- Smaller batch size (4) with gradient accumulation
- Try different optimizer (AdamW vs SGD)

**Fallback:**
- Use smaller base model (ModernBERT-small, 22M params)
- Reduce sequence length (256 tokens)
- Simpler architecture (freeze BERT, train only classifier head)

### Risk 4: Production accuracy <90%

**Mitigation:**
- Collect more training data (expand to 200+ PDFs)
- Improve feature engineering (add font size, spacing)
- Ensemble with Docling baseline (vote or cascade)

**Fallback:**
- Use as filter only (high-recall, low-precision)
- Human-in-the-loop for low-confidence predictions
- Domain-specific fine-tuning (separate law/STEM models)

### Risk 5: Master corpus too large (>2GB)

**Mitigation:**
- Compress with parquet format (better than CSV)
- Store only essential features, drop intermediate columns
- Split into chunks (per journal or per page range)

**Fallback:**
- Process in streaming mode (don't load full corpus)
- Use databases (SQLite) instead of in-memory dataframes

---

## Out of Scope (Future Work)

The following are explicitly **NOT** part of this issue:

- ❌ Cover page classification (cover pages removed at preprocessing)
- ❌ Cross-page context modeling (Docling doesn't use it)
- ❌ Multi-document training (each PDF independent)
- ❌ Non-English documents
- ❌ Non-academic document types (contracts, reports, etc.)
- ❌ Real-time inference optimization (handled in cite-assist deployment)
- ❌ GPU optimization (can train on CPU if needed)

These may be addressed in future issues (v4, v5, etc.)

---

## Deliverables Checklist

### Data Artifacts

- [ ] `data/corpus_v3_pdf_selection.json` - PDF selection manifest
- [ ] `data/docling_raw_extraction_v3.csv` - Raw Docling features
- [ ] `data/master_corpus_v3_labeled.csv` - HTML-labeled paragraphs
- [ ] `data/master_corpus_v3_complete.csv` - Final master corpus (500K-800K)
- [ ] `data/train_corpus_v3_balanced.csv` - Training set (balanced)
- [ ] `data/val_corpus_v3_balanced.csv` - Validation set
- [ ] `data/test_corpus_v3_balanced.csv` - Test set

### Documentation

- [ ] `docs/CORPUS_V3_STATISTICS.md` - Corpus statistics report
- [ ] `docs/CORPUS_V3_BUILD_REPORT.md` - Build process documentation
- [ ] `docs/CORPUS_V3_SAMPLING_STRATEGY.md` - Sampling methodology
- [ ] `models/doclingbert-v3/MODEL_CARD.md` - Model documentation
- [ ] `models/doclingbert-v3/EVALUATION_REPORT.md` - Performance metrics

### Model Artifacts

- [ ] `models/doclingbert-v3/pytorch_model.bin` - Model weights
- [ ] `models/doclingbert-v3/config.json` - Model config
- [ ] `models/doclingbert-v3/tokenizer_config.json` - Tokenizer config
- [ ] `models/doclingbert-v3/label_map.json` - Label mapping + metadata
- [ ] `models/doclingbert-v3/training_args.json` - Training hyperparameters

### Scripts

- [ ] `scripts/corpus_building/extract_docling_features.py`
- [ ] `scripts/corpus_building/match_html_labels.py`
- [ ] `scripts/corpus_building/build_master_corpus_v3.py`
- [ ] `scripts/corpus_building/sample_training_corpus.py`
- [ ] `scripts/analysis/analyze_corpus_v3.py`
- [ ] Update `scripts/training/train_multiclass_classifier.py` for new format

---

## Related Issues

- Issue #8: Improve body_text recall (rebalance class weights) - superseded by this approach
- Issue #7: DoclingBERT v2 quick test - baseline comparison
- Issue #30: Non-law collection infrastructure - provides STEM diversity
- Issue #35: Platform cover regex filtering - preprocessing step
- Issue #37: Non-law collection deployment - merged

---

## References

### Documentation

- [TRAINING_QUICK_START.md](../guides/TRAINING_QUICK_START.md) - Training workflow
- [cite-assist/docs/guides/doclingbert-upgrade.md](../../../cite-assist/docs/guides/doclingbert-upgrade.md) - Deployment guide
- [cite-assist/docs/guides/classifier-service.md](../../../cite-assist/docs/guides/classifier-service.md) - Production API

### Existing Corpus Files (to be replaced)

- `data/clean_7class_corpus.csv` - Current flawed corpus (3 classes only)
- `data/8class_corpus.csv` - Older version
- `data/labeled_pdf_corpus.csv` - HTML-PDF matches (incomplete)
- `data/full_docling_corpus.csv` - Raw Docling output (reference only)

### Code References

- ModernBERT: https://huggingface.co/answerdotai/ModernBERT-base
- Docling: https://github.com/DS4SD/docling
- Current training: `scripts/training/train_multiclass_classifier.py:90`

---

## Acceptance Criteria

This issue is complete when:

1. ✅ Master corpus created with 500K-800K labeled paragraphs
2. ✅ All 7 semantic classes represented (≥1% each)
3. ✅ HTML match rate ≥70%
4. ✅ Training corpus sampled (20K-30K balanced)
5. ✅ DoclingBERT v3 trained and evaluated
6. ✅ Overall accuracy ≥95%, body_text recall ≥80%
7. ✅ Model packaged and documented
8. ✅ Deployment guide updated
9. ✅ All deliverables committed to repository
10. ✅ Model tested in cite-assist classifier service

---

## Notes

- This is a **complete rebuild**, not an incremental fix
- Old corpus files will be archived, not deleted (for reference)
- Master corpus is the source of truth - sampling is deterministic and reproducible
- Focus on flexibility: build complete data infrastructure once, iterate rapidly on modeling
- Production alignment: mirror Docling's page-by-page processing, use realistic class distributions

---

**Estimated effort:** 11-13.5 hours (1-2 days)
**Priority:** High (blocks DoclingBERT v3 production deployment)
**Assignee:** TBD
**Labels:** `enhancement`, `corpus-building`, `machine-learning`, `high-priority`
