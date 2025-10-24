# Active Learning Pipeline for Document Classification

**Status:** In Development
**Last Updated:** 2025-10-23

## Overview

This pipeline trains a custom ModernBERT classifier to replace Docling for law review PDF text extraction. It uses active learning to minimize manual labeling while achieving high accuracy on 4-class document structure classification.

## Pipeline Stages

### Stage 1: Prepare PDF for OCR

**Goal:** Create image-only PDF to ensure training data matches production OCR output

**Script:** `scripts/corpus_building/create_image_only_pdf.py`

**Process:**
1. Open original PDF with PyMuPDF
2. Rasterize each page to greyscale image at 300 DPI
3. Create new PDF with only images (no embedded text)
4. Save as `{pdf_name}_image_only.pdf`

**Why:** Ensures training data comes from OCR (not embedded text), matching production behavior

**Command:**
```bash
uv run python scripts/corpus_building/create_image_only_pdf.py --pdf political_mootness
```

---

### Stage 2: OCR Text Extraction

**Goal:** Extract text blocks with positions and features using best OCR engine

**Script:** `scripts/corpus_building/extract_with_ocr.py` (to be created)

**Process:**
1. Run OCR on image-only PDF (Tesseract/EasyOCR/PaddleOCR)
2. Extract text blocks with bounding boxes
3. Calculate features:
   - `page_number` - Absolute page number (1-indexed)
   - `y_position_normalized` - Vertical position [0.0, 1.0]
   - `normalized_font_size` - Font size relative to page median
   - `text` - Normalized text content
4. Normalize text for RAG:
   - Smart quotes (' ' " ") → straight quotes (' ")
   - Em/en dashes (— –) → hyphen (-)
   - Keep: letters, numbers, basic punctuation, §¶[]
   - Remove: emoji, control chars, other unicode
5. Save as `{pdf_name}_blocks_v1.csv`

**OCR Engine Selection:** Compare engines on normalized text output (see Stage 2a)

**Command:**
```bash
uv run python scripts/corpus_building/extract_with_ocr.py --pdf political_mootness --engine tesseract
```

---

### Stage 2a: OCR Engine Comparison (First Time Only)

**Goal:** Select best OCR engine by comparing normalized text output quality

**Script:** `scripts/evaluation/compare_ocr_engines.py` (to be created)

**Process:**
1. Run each OCR engine on same image-only PDF:
   - Tesseract (CPU-only, free)
   - EasyOCR (CUDA-only, PyTorch-based)
   - PaddleOCR (CUDA-only, PaddlePaddle-based)
   - ocrmypdf (Tesseract wrapper with preprocessing)
2. Normalize all extracted text using `normalize_text_for_rag()`
3. Compare against ground truth HTML (if available)
4. Metrics:
   - Character accuracy
   - Word accuracy
   - Layout preservation (line/paragraph breaks)
   - Speed (pages/second)
   - Memory usage
5. Select best engine for pipeline

**Command:**
```bash
uv run python scripts/evaluation/compare_ocr_engines.py --pdf political_mootness
```

**Output:**
- Comparison report with metrics
- Recommendation for production use

---

### Stage 3: Auto-Labeling (Reduce Manual Work)

**Goal:** Automatically label 70-80% of blocks to minimize human review time

**Script:** `scripts/corpus_building/extract_text_blocks_simple.py` (modify for OCR input)

**Process:**

**3a. HTML Fuzzy Matching (if ground truth HTML available):**
1. Load ground truth HTML from `data/v3_data/processed_html/{pdf_name}.json`
2. Extract body text and footnotes from HTML
3. Fuzzy match OCR blocks against HTML:
   - Match threshold: 80% similarity (RapidFuzz)
   - Body text → label `body_text`
   - Footnotes → label `footnote`
4. Mark unmatched blocks as `NEEDS_REVIEW`

**3b. Model Predictions (if trained model exists):**
1. Load best ModernBERT checkpoint
2. Run predictions on `NEEDS_REVIEW` blocks
3. If confidence > 0.8, auto-label with predicted class
4. If confidence ≤ 0.8, keep as `NEEDS_REVIEW`

**Output:** `{pdf_name}_blocks_v2_predicted.csv`

**Statistics:**
- Typically 70-80% auto-labeled via HTML
- 10-20% auto-labeled via model
- 10% require manual review

---

### Stage 4: Generate Human-in-Loop Materials

**Goal:** Create visual tools for efficient human review

**Script:** `scripts/visualization/visualize_text_block_classes.py`

**Process:**
1. Load `{pdf_name}_blocks_v2_predicted.csv`
2. Create color-coded PDF overlay:
   - Green (body_text)
   - Blue (footnote)
   - Purple (front_matter)
   - Yellow (header)
   - Red (NEEDS_REVIEW)
3. Save as `{pdf_name}_annotated.pdf`

**Output:**
- `{pdf_name}_annotated.pdf` - Visual review tool
- `{pdf_name}_blocks_v2_predicted.csv` - Data for manual correction

**Command:**
```bash
uv run python scripts/visualization/visualize_text_block_classes.py --csv {pdf_name}_blocks_v2_predicted.csv
```

---

### Stage 5: Human Review & Correction

**Goal:** Manually correct labels to create high-quality training data

**Process:**
1. Open `{pdf_name}_annotated.pdf` for visual reference
2. Open `{pdf_name}_blocks_v2_predicted.csv` in spreadsheet
3. For each `NEEDS_REVIEW` block:
   - Read text content
   - Check position in annotated PDF
   - Assign correct label: `body_text`, `footnote`, `front_matter`, or `header`
4. Review auto-labeled blocks (spot check ~10%)
5. Apply footer merge rules:
   - Footer on page 1 → `front_matter`
   - Footer on page > 1 → `footnote`
6. Save as `{pdf_name}_blocks_v3_labeled.csv`

**Quality Check:**
- All blocks should have a label (no `NEEDS_REVIEW` remaining)
- Verify label distribution makes sense (e.g., body_text > 40%)

**Output:** `{pdf_name}_blocks_v3_labeled.csv` - Training data

---

### Stage 6: Training

**Goal:** Train/fine-tune ModernBERT on corrected labels

**Script:** `scripts/training/train_simple_classifier.py`

**Process:**
1. Load all `*_v3_labeled.csv` files
2. Combine into single training dataset
3. Split: 80% train, 20% validation
4. Fine-tune ModernBERT:
   - Base: ModernBERT-base (149M params)
   - Features: text (ModernBERT) + position features (linear encoder)
   - Classes: 4 (body_text, footnote, front_matter, header)
   - Epochs: 10
   - Device: MPS (Apple Silicon GPU)
5. Save checkpoints every epoch
6. Select best checkpoint by validation accuracy

**Model Architecture:**
```python
class SimpleTextBlockClassifier(ModernBertPreTrainedModel):
    def __init__(self, num_labels=4):
        self.modernbert = ModernBertModel(config)
        self.position_encoder = nn.Linear(3, 768)  # 3 position features
        self.classifier = nn.Linear(768 + 768, 4)  # text + position → 4 classes
```

**Command:**
```bash
# Train on single document
uv run python scripts/training/train_simple_classifier.py --csv {pdf_name}_blocks_v3_labeled.csv --epochs 10

# Train on combined documents
uv run python scripts/training/train_simple_classifier.py --csv combined_docs_v3_labeled.csv --epochs 10
```

**Output:**
- `models/simple_text_classifier/checkpoints/checkpoint-{N}/` - All checkpoints
- `models/simple_text_classifier/final_model/` - Best model

**Monitoring:**
- Training loss should decrease
- Validation accuracy should increase
- Watch for overfitting (val loss increases while train loss decreases)

---

### Stage 7: Active Learning Loop

**Goal:** Iteratively improve model with diverse training examples

**Strategy:**
1. **Document diversity** (prioritize):
   - Layout variety: 1-column, 2-column, mixed
   - Footnote density: high (>50%), medium (20-50%), low (<20%)
   - Document length: short (<25 pages), medium (25-50), long (>50)
   - Special features: tables, figures, appendices
2. **Error-driven selection:**
   - If model struggles with specific patterns, find similar documents
   - E.g., low front_matter accuracy → add more TOC-heavy documents
3. **Diminishing returns:**
   - Stop when validation accuracy plateaus
   - Typical target: 5-10 labeled documents, 95%+ accuracy

**Process:**
1. Select next PDF from corpus (prioritize diversity)
2. Run Stages 1-6 on new PDF
3. Combine with existing training data
4. Retrain model
5. Evaluate accuracy improvement
6. Repeat if improvement > 1%

**Stopping Criteria:**
- Validation accuracy > 95%
- Accuracy improvement < 1% for 2 consecutive documents
- All major layout patterns represented

---

## Current Status

### Completed Documents
- ❌ **Document 1:** `texas_law_review_extraterritoriality-patent-infringement`
  - Status: Extracted from **embedded text** (not OCR)
  - Action: Re-extract using image→OCR pipeline
  - Labeled blocks: 170 (97 body, 30 footnote, 13 front_matter, 30 header)

- ❌ **Document 2:** `michigan_law_review_law_enforcement_privilege`
  - Status: Extracted from **embedded text** (not OCR)
  - Action: Re-extract using image→OCR pipeline
  - Labeled blocks: 512 (194 body, 241 footnote, 20 front_matter, 57 header)

### Model Status
- **Best checkpoint:** Epoch 8/10, 97.06% accuracy
- **Issue:** Trained on embedded text, not OCR output
- **Action:** Retrain after re-extracting documents 1+2 via OCR

### Next Steps
1. ✅ Document pipeline (this file)
2. ⏳ Compare OCR engines on normalized text
3. ⏳ Re-extract document 1 using image→OCR
4. ⏳ Re-extract document 2 using image→OCR
5. ⏳ Retrain model on OCR data
6. ⏳ Extract document 3 (diverse selection)

---

## Class Definitions

### 1. body_text
**Definition:** Main article content

**Characteristics:**
- In HTML body (if HTML available)
- Middle of page (0.1 < y < 0.9)
- Median font size (0.9 < normalized_font_size < 1.2)
- Longest text blocks
- No special formatting (not citations, not titles)

**Examples:** Paragraphs, sentences, analysis

---

### 2. footnote
**Definition:** Citations, references, and page footers (page > 1)

**Characteristics:**
- In HTML footnotes (if HTML available) OR
- Bottom of page (y > 0.9) AND page_number > 1
- Smaller font (normalized_font_size < 0.9)
- Often starts with numbers (1., 2., etc.) or symbols (*, †)

**Examples:** Case citations, scholarly references, page numbers on page 2+

**Note:** Page 1 footers merged into `front_matter` (contextual grouping)

---

### 3. front_matter
**Definition:** Title, abstract, author, TOC, first-page footer

**Characteristics:**
- NOT in HTML (unique to PDF) OR on pages 1-3
- Larger font for title (normalized_font_size > 1.3)
- Special formatting: centered, bold, all-caps
- Dotted leaders (TOC entries)
- First page footer (y > 0.9, page_number == 1)

**Examples:** Article title, author names, abstract, table of contents, page 1 footer

**Merge Rules:**
- Footer on page 1 → `front_matter` (part of front matter)
- TOC entries → `front_matter` (not separate class)

---

### 4. header
**Definition:** Page headers (running headers)

**Characteristics:**
- Top of page (y < 0.1)
- Repeated across pages
- Smaller font (normalized_font_size < 1.0)
- Often includes: page numbers, journal name, article title

**Examples:** "2024 TEXAS LAW REVIEW 123", page numbers at top

---

## Text Normalization Rules

**Applied during:** Stage 2 (OCR extraction)

**Function:** `normalize_text_for_rag(text: str) -> str`

**Keep:**
- English letters (a-z, A-Z)
- Numbers (0-9)
- Basic punctuation: . , ! ? : ; ' " - ( ) / &
- Legal symbols: § ¶
- Brackets: [ ] (heading indicators)
- Accented Latin characters: á é í ó ú ñ ä ö ü (proper names)
- Whitespace

**Normalize:**
- Smart quotes (' ' " ") → straight quotes (' ")
- Em dash (—) → hyphen (-)
- En dash (–) → hyphen (-)
- Multiple spaces/tabs → single space

**Remove:**
- Emoji (U+1F600+)
- Control characters (U+0000-U+001F, U+007F-U+009F)
- Other unicode symbols not listed above

**Rationale:** Clean text for RAG, improve search/matching, reduce token diversity

---

## File Naming Convention

**Versioning:**
- `v1` - Initial extraction (OCR output)
- `v2_predicted` - Auto-labeled + model predictions
- `v3_labeled` - Human-corrected labels (training data)

**Example Files:**
```
data/v3_data/raw_pdf/political_mootness.pdf                          # Original PDF
results/ocr_pipeline/political_mootness_image_only.pdf               # Image-only PDF
results/text_block_extraction/political_mootness_blocks_v1.csv       # OCR extraction
results/text_block_extraction/political_mootness_blocks_v2_predicted.csv # Auto-labeled
results/text_block_extraction/political_mootness_annotated.pdf       # Visual review
results/text_block_extraction/political_mootness_blocks_v3_labeled.csv # Training data
```

---

## Performance Targets

**Auto-Labeling (Stage 3):**
- HTML matching: 70-80% of blocks
- Model predictions: 10-20% of blocks
- Manual review: <10% of blocks

**Training (Stage 6):**
- Validation accuracy: >95%
- Per-class recall: >90%
- Training time: <5 minutes per document on MPS

**Production (Future):**
- Overall recall: >98% (vs 89-93% with Docling)
- TOC recall: >95% (vs 0% with Docling)
- Body text recall: >98%

---

## Tools & Dependencies

**Core Libraries:**
- `pymupdf` - PDF manipulation, image conversion
- `pytesseract` / `easyocr` / `paddleocr` - OCR engines
- `transformers` - ModernBERT fine-tuning
- `torch` - Neural network training (MPS support)
- `pandas` - CSV manipulation
- `rapidfuzz` - Fuzzy text matching
- `numpy` - Feature calculation

**Hardware:**
- MPS (Apple Silicon GPU) - ModernBERT training
- CPU - OCR (Tesseract), PDF processing

---

## Troubleshooting

**Issue:** OCR produces garbled text
- **Solution:** Check image quality (DPI ≥ 300), try different OCR engine

**Issue:** Auto-labeling accuracy < 70%
- **Solution:** Check HTML ground truth quality, lower fuzzy match threshold

**Issue:** Training accuracy plateaus < 95%
- **Solution:** Add more diverse documents, check for labeling errors

**Issue:** Memory pressure during training
- **Solution:** Reduce batch size, use cite-assist service for embeddings

**Issue:** Model overfits (train >> val accuracy)
- **Solution:** Add more training data, reduce epochs, add regularization

---

*Last updated: 2025-10-23*
