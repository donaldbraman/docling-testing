# V3 Corpus Data Pipeline

This directory contains all data for building the v3 training corpus for ModernBERT.

## Pipeline Overview

```
raw_html + raw_pdf → docling_extraction → relabeled_extraction → ModernBERT Training
```

## Directory Structure

### 1. `raw_html/`
**Ground truth HTML files** - Source of correct semantic labels

- HTML files from law review journals with known structure
- Used to generate ground truth labels for body_text, footnotes, etc.
- Files must be paired with corresponding PDFs

### 2. `raw_pdf/`
**PDF files to be labeled**

- Law review articles in PDF format
- Each PDF should have a corresponding HTML file for ground truth
- Naming convention: `{journal}_{article_slug}.pdf`

### 3. `docling_extraction/`
**Initial Docling extractions**

- Output from Docling's automatic PDF extraction
- Contains Docling's predicted labels (often incorrect for body_text vs footnotes)
- JSON format with text blocks and predicted labels

### 4. `relabeled_extraction/`
**Corrected labels using HTML ground truth**

- Docling extractions with labels corrected by matching to HTML
- Final training data for ModernBERT
- JSON format: `{text, label, confidence, source}`

### 5. `processed_html/`
**Normalized/cleaned HTML files**

- HTML files after extraction and normalization
- Intermediate processing artifacts
- JSON format with extracted paragraphs and labels

## Workflow

1. **Pair verification**: Ensure each PDF has corresponding HTML
2. **HTML extraction**: Extract ground truth labels from HTML
3. **Docling extraction**: Run Docling on PDFs
4. **Label matching**: Match PDF paragraphs to HTML paragraphs
5. **Label correction**: Override Docling labels with HTML ground truth
6. **Corpus assembly**: Combine all relabeled data for training

## Naming Convention

All files use consistent naming:
```
{journal}_{article_slug}.{ext}
```

Examples:
- `michigan_law_review_law_enforcement_privilege.html`
- `michigan_law_review_law_enforcement_privilege.pdf`
- `michigan_law_review_law_enforcement_privilege.json`

## Quality Control

- All HTML-PDF pairs must be validated
- Footnote counts must match between HTML and PDF
- Body text extraction must be verified manually for sample articles

---

Created: 2025-10-17
Pipeline: v3 (Pure Positive Inclusion)
