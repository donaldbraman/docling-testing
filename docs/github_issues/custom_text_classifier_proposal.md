# Custom Text Classification Pipeline to Replace Docling

**Status:** ✅ **IN PROGRESS** - Active learning pipeline implemented, training on document 2/N

## Problem Statement

Docling discards 12% of successfully OCR'd text due to layout classification filtering that cannot be fixed through configuration. Specifically:

- **Root cause:** DocLayNet training data lacks law review TOC patterns
- **Symptom:** TOC entries (dotted leaders, hierarchical indentation, mixed alignment) rejected as "ambiguous"
- **Impact:** 89-93% recall on academic PDFs vs 96%+ on simple documents
- **Cannot fix with:**
  - Configuration changes (tested 6 configs → +0 words)
  - Confidence threshold lowering (0.3 → 0.1 → +0 words)
  - Post-processing (text filtered before output)

**Evidence:** See `docs/LAYOUT_DETECTION_INVESTIGATION_SUMMARY.md` and `docs/docling_max_recall.md`

## Current Implementation (Updated 2025-10-23)

### Active Learning Pipeline (Implemented)

We've implemented Option 1 with significant simplifications based on empirical findings:

**Architecture:**
```
PDF → PyMuPDF text extraction
    → 4 simple features (page_number, y_position, normalized_font_size, text)
    → Semi-automatic HTML matching (70-80% auto-labeled)
    → ModernBERT predictions on remaining blocks (20-30%)
    → Human review/correction
    → Retrain on corrected data
    → Repeat for next document (active learning)
```

**Key Simplifications:**
1. **Reduced to 4 classes** (from 5):
   - `body_text` - Main article content
   - `footnote` - Citations + page footers (merged - both at bottom, y > 0.9)
   - `front_matter` - Title, abstract, author, TOC (all first-page non-body content)
   - `header` - Page headers (top of page, y < 0.1)

2. **Versioned workflow**:
   - `v1`: HTML fuzzy matching only (70-80% auto-labeled)
   - `v2_predicted`: Model predictions + confidence scores (20-30% blocks)
   - `v3_labeled`: Human-corrected labels (training data)

3. **Simplified features** (4 total, down from 20+ in original proposal):
   - Only the most discriminative features retained
   - ModernBERT handles semantic complexity via text

**Current Progress:**
- ✅ Scripts implemented: `extract_text_blocks_simple.py`, `predict_and_extract.py`, `visualize_text_block_classes.py`
- ✅ Document 1 labeled: 170 blocks (97 body, 30 footnote, 13 front_matter, 30 header)
- ✅ Document 2 labeled: 512 blocks (194 body, 241 footnote, 20 front_matter, 57 header)
- ✅ Combined training: 682 blocks total
- 🔄 Training epoch 2/10 (86.3% accuracy on validation)

**Model Architecture:**
```python
class SimpleTextBlockClassifier(ModernBertPreTrainedModel):
    def __init__(self, num_labels=4):
        self.modernbert = ModernBertModel(config)
        self.position_encoder = nn.Linear(3, 768)  # 3 position features
        self.classifier = nn.Linear(768 + 768, 4)  # text + position → 4 classes
```

**Why 4 Classes Works:**

1. **Footer → Footnote merge** (Positional clustering)
   - Both at bottom of page (y > 0.9)
   - ModernBERT distinguishes via text length (footers: < 20 chars, footnotes: longer)
   - Page 1 footers contextually grouped with `front_matter`

2. **TOC → Front matter merge** (Simplification)
   - TOC only appears on first few pages
   - Semantically part of front matter
   - Dotted leaders still learned as pattern within `front_matter` class

**Findings:**
- Law review PDFs rarely have running footers (only 2 of 254 PDFs!)
- Most "footers" are just page numbers on page 1 (part of front matter)
- Active learning reduces manual labeling: 70-80% auto-labeled via HTML matching

**Next Steps:**
1. Complete training on docs 1+2 (current: epoch 2/10)
2. Extract document 3 with improved model
3. Add 3-5 more diverse documents (different lengths, footnote densities)
4. Evaluate final model on held-out test set

### Cite-Assist Service Integration (Optimization)

**Goal:** Reduce memory footprint and startup time for production inference by leveraging existing cite-assist ModernBERT service.

**Architecture:**
```
Training (local):
  PDF → Features → Full ModernBERT fine-tuning → Save classification head

Inference (service + local):
  PDF → Features → cite-assist service (embeddings)
                 → Local classification head (< 1MB)
                 → Predictions
```

**Benefits:**
- **Memory savings:** ~600MB (avoid loading full ModernBERT model)
- **Faster startup:** Model already loaded in cite-assist service
- **Reuse infrastructure:** Leverage existing optimized service
- **Minimal local resources:** Only classification head (~1MB) + position encoder (~2KB)

**Implementation Plan:**

1. **Training phase** (no change):
   - Continue current approach: Fine-tune full ModernBERT locally
   - Save both full model and classification head separately

2. **Inference phase** (optimization):
   - Extract text blocks with 4 features (same as current)
   - Call cite-assist service API for text embeddings (768-dim vectors)
   - Load lightweight classification head locally
   - Combine: `embeddings + position_features → classifier → predictions`

3. **API integration:**
   ```python
   # Instead of loading full model:
   # model = SimpleTextBlockClassifier.from_pretrained(model_dir)

   # Use cite-assist service + local head:
   embeddings = cite_assist_client.get_embeddings(texts)
   classifier_head = torch.load("classification_head.pt")
   predictions = classifier_head(embeddings, position_features)
   ```

**Status:** Proposed optimization for Phase 3 (Production Model) - cite-assist service already running locally

---

## Original Proposal (Reference)

## Proposed Solution

Build custom text classification pipeline using ModernBERT to achieve 100% text recall with accurate semantic classification.

## Option 1: Raw OCR + ModernBERT Classifier (Recommended)

### Architecture

```
PDF → Raw OCR (PyMuPDF/ocrmac)
    → Text blocks with coordinates
    → Feature extraction (4 simple features)
    → ModernBERT encoder + positional embeddings
    → Classification head (5 classes)
    → Labeled text blocks (100% recall)
```

### Classes (Updated to 4)

**Current implementation uses 4 classes:**

1. **body_text** - Main article content (IN HTML body)
2. **footnote** - Citations/references + page footers (IN HTML footnotes, OR bottom of page)
3. **front_matter** - Title, abstract, author, TOC (NOT in HTML, pages 1-3)
4. **header** - Page headers (NOT in HTML, repeated, top of page)

**Original proposal had 5 classes, but `footer` was merged into `footnote`** due to:
- Positional similarity (both y > 0.9)
- Scarcity of running footers in law review PDFs (2 of 254)
- Text length distinguishes them (footers < 20 chars)

### Implementation Plan

#### Phase 1: Text Extraction (Week 1)
1. **Extract text blocks with 4 simple features**
   - Use PyMuPDF's `page.get_text("dict")` for text + bounding boxes + font data
   - Output: `(text, page_number, y_position_normalized, normalized_font_size)`

2. **Feature set (4 features only)**

   **Feature 1: page_number** (integer, 1-indexed)
   - Identifies front_matter (pages 1-3 pattern)
   - ModernBERT learns: "early page + not in HTML → front_matter"

   **Feature 2: y_position_normalized** (float, 0.0 to 1.0)
   - Vertical position on page (0.0 = top, 1.0 = bottom)
   - Separates header (y ~0.0) from footer (y ~1.0) from body (y ~0.1-0.9)
   - ModernBERT learns: "y < 0.1 → header, y > 0.9 → footer"

   **Feature 3: normalized_font_size** (float, relative to page median)
   - Font size / median page font size
   - Distinguishes: footnotes (0.7-0.9x), body (1.0x), headers (1.2-1.4x), titles (1.5-2.0x)
   - ModernBERT learns: "font < 0.9x + y > 0.9 → footnote"

   **Feature 4: text** (string, for ModernBERT semantic understanding)
   - Semantic patterns: dotted leaders (TOC), citation patterns, etc.
   - ModernBERT learns content-based classification

3. **Why font size is critical**

   Font size is the **strongest single feature** for classification in law review PDFs:

   | Element Type | Typical Font Size | Relative Size |
   |-------------|------------------|---------------|
   | Title | 16-20pt | 1.5-2.0x body |
   | Section Header | 12-14pt | 1.2-1.4x body |
   | Body Text | 10-11pt | 1.0x (baseline) |
   | TOC Entry | 9-11pt | 0.9-1.1x body |
   | Footnote | 8-9pt | 0.7-0.9x body |
   | Page Header/Footer | 8-9pt | 0.7-0.9x body |

   **Key patterns:**
   - Section headers: Larger + bold
   - Footnotes: Smaller + bottom of page
   - TOC entries: Mixed sizes + dotted leaders + right-aligned numbers
   - Page headers/footers: Small + top/bottom margin

   **Example classification logic ModernBERT learns:**
   ```
   if font_size > 1.3x AND is_bold AND distance_from_top < 100:
       → section_header (high confidence)

   if font_size < 0.9x AND distance_from_bottom < 50:
       → footnote (high confidence)

   if has_dotted_leaders AND has_trailing_number AND 0.9x < font_size < 1.1x:
       → toc_entry (high confidence)
   ```

   This is much more robust than Docling's pure visual pattern matching!

#### Phase 2: Data Preparation (Week 1-2)
1. **Augment existing labeled dataset**
   - Current: 37,888 paragraphs across 6 semantic classes
   - Need: Add TOC labels (~500-1000 examples)
   - Method:
     - Semi-automatic: Extract page 1-5 from all PDFs, filter lines with dotted leaders
     - Manual review: Label 50-100 TOC examples
     - Weak supervision: Use Docling's labels for non-TOC content (they're accurate for standard layouts)

2. **Create training dataset**
   - Format: `(text, position_features, typography_features) → label`
   - Split: 80% train, 10% val, 10% test
   - Stratified by class (ensure TOC representation)

#### Phase 3: Model Development (Week 2)
1. **ModernBERT fine-tuning**
   - Base model: ModernBERT-base (149M parameters) - already familiar
   - Architecture:
     ```python
     class TextBlockClassifier(nn.Module):
         def __init__(self):
             self.bert = ModernBertModel.from_pretrained("answerdotai/ModernBERT-base")
             self.position_encoder = nn.Linear(feature_dim, 768)
             self.classifier = nn.Linear(768 + 768, num_classes)

         def forward(self, text_ids, position_features):
             text_emb = self.bert(text_ids).last_hidden_state[:, 0, :]  # [CLS]
             pos_emb = self.position_encoder(position_features)
             combined = torch.cat([text_emb, pos_emb], dim=-1)
             return self.classifier(combined)
     ```

2. **Training configuration**
   - Same setup as DoclingBERT training (existing experience)
   - Loss: CrossEntropyLoss with class weights
   - Optimizer: AdamW, learning rate 2e-5
   - Batch size: 32
   - Epochs: 10
   - Early stopping on validation F1

#### Phase 4: Evaluation & Refinement (Week 3)
1. **Evaluate on test set**
   - Metrics: Precision, Recall, F1 per class
   - Compare to Docling baseline
   - Target: >95% recall on TOC entries, maintain >90% overall accuracy

2. **Error analysis**
   - Visualize misclassifications
   - Identify additional features needed
   - Refine model architecture if needed

3. **Integration testing**
   - Run on all 254 corpus PDFs
   - Compare output to ground truth
   - Measure end-to-end recall improvement

### Advantages

✅ **100% text recall** - No filtering, every text block classified
✅ **Domain-specific** - Trained on law review PDFs specifically
✅ **TOC-aware** - Explicitly learns TOC patterns (dotted leaders, mixed alignment, etc.)
✅ **Robust** - ModernBERT handles variation better than regex
✅ **Extensible** - Easy to add new classes or refine features
✅ **Maintainable** - Full control over model and training
✅ **Leverage existing infrastructure** - Training pipeline, evaluation, labeled data already exist

### Disadvantages

❌ **Development time** - 2-3 weeks full implementation
❌ **Need TOC labels** - 500-1000 additional examples to label
❌ **Maintenance** - Responsible for model updates, retraining
❌ **Loses Docling features** - Would need to reimplement table detection, figure extraction

### Estimated Effort

- **Text extraction:** 2-3 days (mostly reusing existing code)
- **Feature engineering:** 3-4 days (calculate positional features)
- **Data labeling:** 3-5 days (semi-automatic TOC detection + manual review)
- **Model training:** 2-3 days (similar to DoclingBERT)
- **Evaluation:** 2-3 days (reuse existing evaluation pipeline)
- **Integration:** 2-3 days (replace Docling calls)

**Total: 2-3 weeks** (assuming full-time work)

## Option 2: Hybrid Approach (Faster Alternative)

### Architecture

```
PDF → Page-level TOC detection
    → If TOC page: Custom classifier or simple rules
    → If non-TOC: Docling pipeline
    → Merge outputs
```

### Implementation

1. **TOC page detector**
   - Simple heuristics: page_num < 5 AND (has_dotted_leaders OR hierarchical_indentation)
   - Or: Train lightweight classifier on page images

2. **TOC text handler**
   - Option A: Simple rules (if has dotted leader → toc_entry)
   - Option B: ModernBERT classifier (just for TOC pages)

3. **Keep Docling for non-TOC**
   - Leverage existing table detection, figure extraction
   - Use Docling's classifications for standard layouts

### Advantages

✅ **Faster development** - 1-2 weeks vs 2-3 weeks
✅ **Keep Docling strengths** - Table detection, figure extraction, etc.
✅ **Focused effort** - Solve TOC problem specifically
✅ **Less risk** - Smaller code change

### Disadvantages

❌ **Heuristic TOC detection** - May miss or misclassify TOC pages
❌ **Still limited by Docling** - Other edge cases remain (citations, multi-column, etc.)
❌ **More complex pipeline** - Two different code paths to maintain

## Option 3: Fork Docling (Not Recommended)

Fork Docling and replace classification stage with custom logic.

**Advantages:** Leverage existing layout detection model
**Disadvantages:**
- High complexity (need to understand Docling internals)
- Maintenance burden (breaks on upstream updates)
- Limited benefit (layout detection works, classification is the problem)

**Not recommended.**

## Data Assets (Already Available)

✅ **Labeled corpus:** 37,888 paragraphs across 7 classes
✅ **Training pipeline:** Existing scripts for ModernBERT training
✅ **Evaluation pipeline:** Metrics calculation, confusion matrices, diff visualization
✅ **OCR pipeline:** Raw text extraction with coordinates
✅ **Ground truth:** HTML-PDF alignments for 254 PDFs

**Need to add:** TOC labels (~500-1000 examples)

## Success Metrics

### Target Performance
- **Overall recall:** >98% (vs 89-93% with Docling)
- **TOC recall:** >95% (vs 0% with Docling)
- **Body text recall:** >98% (maintain current ~98%)
- **Footnote recall:** >90% (maintain current ~85%)

### Evaluation Method
- Test on held-out set of 25 PDFs (10% of corpus)
- Compare classified output to ground truth HTML
- Measure precision, recall, F1 per class
- Visual inspection of difficult cases

## Implementation Checklist (Updated)

### Phase 1: Active Learning Pipeline ✅ COMPLETE
- [x] Implement text extraction with 4 features (`extract_text_blocks_simple.py`)
- [x] Implement semi-automatic HTML matching (70-80% auto-labeled)
- [x] Implement model prediction script (`predict_and_extract.py`)
- [x] Implement color-coded visualization (`visualize_text_block_classes.py`)
- [x] Implement versioned workflow (v1 → v2 → v3)
- [x] Label document 1 (170 blocks)
- [x] Label document 2 (512 blocks)
- [x] Train ModernBERT classifier on combined data (682 blocks)

### Phase 2: Iterative Improvement 🔄 IN PROGRESS
- [x] Simplify from 5 to 4 classes (merge footer → footnote)
- [x] Update all scripts for 4-class system
- [x] Retrain on documents 1+2 combined (current: epoch 2/10)
- [ ] Extract document 3 with improved model
- [ ] Add 3-5 more diverse documents
  - [ ] High footnote density document
  - [ ] Minimal footnotes document
  - [ ] Short document (< 25 pages)
  - [ ] Long document (> 50 pages)
- [ ] Evaluate accuracy trends as training data grows

### Phase 3: Production Model 🔜 NEXT
- [ ] Train final model on 5-10 labeled documents
- [ ] Evaluate on held-out test set
- [ ] Compare recall to Docling baseline
- [ ] Generate confusion matrix and error analysis
- [ ] Document model performance metrics

### Phase 4: Integration (Future)
- [ ] Replace Docling calls with custom classifier
- [ ] Run full corpus evaluation (254 PDFs)
- [ ] Generate comparison report (Docling vs Custom)
- [ ] Add text normalization (smart quotes, unicode, etc.)
- [ ] Package as reusable library

## Alternative: Stay with Docling + Reconciliation

If custom classifier is too much work, use programmatic reconciliation (already documented in `docs/docling_max_recall.md`):

1. Extract raw OCR output (100% recall)
2. Process with Docling (semantic structure)
3. Compare outputs, re-insert missing text
4. Accept that TOC entries are labeled "text" (generic)

**Pros:** Less work (1-2 days)
**Cons:** Lose semantic classification for TOC content

## Recommendation

**Start with Option 1 (Custom ModernBERT Classifier)** because:

1. ✅ Solves root cause (training data bias)
2. ✅ Achieves project goal (accurate semantic classification)
3. ✅ Leverages existing infrastructure (training pipeline, labeled data)
4. ✅ Builds on existing expertise (already trained DoclingBERT models)
5. ✅ Extensible for future improvements (add more classes, refine features)

**Timeline:**
- Week 1: Proof of concept on 10 PDFs
- Week 2-3: Full implementation if PoC successful
- Total: 2-3 weeks to production-ready classifier

## Open Questions

1. **Should we implement table/figure detection?**
   - Option A: Keep Docling just for tables/figures
   - Option B: Use heuristic rules (large images, grid patterns)
   - Option C: Add table/figure classes to ModernBERT classifier

2. **What about multi-column layouts?**
   - ModernBERT doesn't handle reading order
   - May need separate column detection step

3. **Should we support non-law-review PDFs?**
   - Current approach optimized for law reviews
   - Would need more diverse training data for generalization

## References

- Investigation summary: `docs/LAYOUT_DETECTION_INVESTIGATION_SUMMARY.md`
- Max recall analysis: `docs/docling_max_recall.md`
- Configuration tests: `docs/DOCLING_CONFIGURATION_OPTIONS.md`
- Test scripts: `scripts/evaluation/test_lower_confidence_threshold.py`, `scripts/evaluation/compare_raw_ocr_vs_classified.py`

---

**Labels:** enhancement, investigation, model-training, high-priority
**Estimated effort:** 2-3 weeks
**Dependencies:** None (all infrastructure exists)
**Decision needed:** Approve Option 1 vs Option 2 vs stay with Docling reconciliation
