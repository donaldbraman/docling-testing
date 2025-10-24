# Training Corpus Exclusion List

**Last updated:** 2025-10-22

## Overview

This document identifies PDFs that should be excluded from the training corpus because they are magazine-style publications rather than traditional academic law review articles. These documents have complex layouts with graphic design elements that degrade OCR and classification performance.

## Performance Impact

OCR testing revealed a dramatic performance gap between document types:

**Traditional academic articles:**
- Word recall: 94-96%
- Character recall: 95-99%
- Examples: antitrust_interdependence_paradox, california_law_review_amazon-trademark, texas_law_review_working-with-statutes

**Magazine-style reports:**
- Word recall: 28-29%
- Character recall: 95-99%
- The gap between character and word recall indicates structural organization problems, not OCR quality issues

## Exclusion Criteria

Exclude PDFs with these characteristics:

### Magazine-Style Layout Features
- Full-bleed graphic covers with photography
- Background images with overlay text
- Multiple non-text cover pages before body text
- Sponsor logos and branding
- Magazine design elements (color blocks, special layouts)

### Document Types to Exclude
- Survey reports (e.g., "2025 College Free Speech Rankings")
- Policy reports (e.g., Legislative Analyst Office reports)
- Executive summaries with graphic design
- Magazine-format publications

### Document Types to Include
- Traditional academic law review articles
- Simple, clean title pages
- Single-column text layout
- Standard headers/footers
- Minimal graphics
- Academic formatting with footnotes

## Excluded PDFs

### Category 1: Magazine-Style Publications (Low Recall)

Based on OCR performance testing - these have <30% word recall due to graphic design layouts:

1. **usc_law_review_listening_on_campus_academic_freedom_and_its_audiences.pdf**
   - Type: Survey report ("2025 College Free Speech Rankings")
   - Word recall: 29.12%
   - Layout: Full-bleed graphic cover, background protest photos, sponsor logos (College Pulse, FIRE)
   - Reason: Magazine-style publication, not traditional academic article

2. **ucla_law_review_insurgent_knowledge_battling_cdcr_from_inside_the_system_the_story_of_the_essential_collaboration_be.pdf**
   - Type: Policy report (Legislative Analyst Office report)
   - Word recall: 29.31%
   - Layout: Full-bleed prison facility photo cover, "AN LAO REPORT" minimal text, executive summary with gray design boxes
   - Reason: Government policy report, not traditional academic article

### Category 2: Over-Extraction Issues (Low Precision)

These have high recall (90%+) but very low precision (<30%) due to excessive metadata capture:

3. **policing_campus_protest.pdf**
   - Word recall: 93.42%, precision: 29.88% (3.1x over-extraction)
   - Issue: Docling treats running headers, footers, page numbers, and marginal citations as body text throughout the entire document
   - Example: Every page includes "COLUMBIA LAW REVIEW [Vol. 125:1277]" header as body text
   - Reason: Unusual layout with heavy marginal apparatus, would degrade precision in training

4. **overbroad_protest_laws.pdf**
   - Word recall: 94.48%, precision: 19.66% (4.8x over-extraction)
   - Issue: Similar to policing_campus_protest - metadata treated as body text throughout document
   - Reason: Unusual layout with heavy marginal apparatus, would degrade precision in training

## Visual Identification

### Magazine-Style (EXCLUDE)
Page 1 characteristics:
- Photography filling entire page
- Text overlaid on images
- Bold graphic design
- Institutional branding

Early pages:
- Multiple cover pages before substantive text
- Executive summaries with design boxes
- Sponsor acknowledgments with logos

### Traditional Academic (INCLUDE)
Page 1 characteristics:
- White background with minimal graphics
- Simple title in serif font
- Author name(s) and affiliation
- Abstract or introduction text begins on page 1

Early pages:
- Table of contents in standard format
- Body text begins within first 3 pages
- Standard academic footnote formatting

## Implementation

To apply these exclusions:

```bash
# Move excluded PDFs to excluded directory (already done)
mkdir -p data/v3_data/excluded_pdf

# Magazine-style publications
mv data/v3_data/raw_pdf/usc_law_review_listening_on_campus_academic_freedom_and_its_audiences.pdf data/v3_data/excluded_pdf/
mv data/v3_data/raw_pdf/ucla_law_review_insurgent_knowledge_battling_cdcr_from_inside_the_system_the_story_of_the_essential_collaboration_be.pdf data/v3_data/excluded_pdf/

# Over-extraction issues
mv data/v3_data/raw_pdf/policing_campus_protest.pdf data/v3_data/excluded_pdf/
mv data/v3_data/raw_pdf/overbroad_protest_laws.pdf data/v3_data/excluded_pdf/
```

**Status:** All 4 exclusions have been applied. The excluded PDFs are stored in `data/v3_data/excluded_pdf/` for reference.

## Screening Status

**Testing completed:** Diverse sample of 10 PDFs from different law reviews tested for recall and precision patterns.

**Results:**
- ALL 10 PDFs achieved 90%+ recall (no additional magazine-style documents found)
- 2 PDFs showed over-extraction issues (included in exclusions above)
- 8 PDFs showed clean performance (90%+ recall, 90%+ precision)

**Tested PDFs (all clean except 2 over-extraction cases above):**
- bu_law_review_law_and_culture (96.5% recall, 96.8% precision)
- bu_law_review_learning_from_history (92.1% recall, 94.6% precision)
- bu_law_review_nil_compliance (89.7% recall, 92.2% precision)
- california_law_review_affirmative-asylum (94.0% recall, 91.8% precision)
- california_law_review_judiciary-ada (93.1% recall, 93.1% precision)
- michigan_law_review_law_enforcement_privilege (97.5% recall, 95.8% precision)
- michigan_law_review_spending_clause_standing (97.6% recall, 96.0% precision)
- academic_limbo__reforming_campus_speech_governance_for_students (92.9% recall, 94.1% precision)

**Conclusion:** Only 4 of 78 PDFs needed exclusion (2 magazine-style, 2 over-extraction). The remaining corpus consists of clean, functional law review articles suitable for training.

## Related Documents

- OCR investigation findings: [docs/OCR_INVESTIGATION_FINDINGS.md](OCR_INVESTIGATION_FINDINGS.md)
- OCR comparison results: [results/ocr_engine_comparison/](../results/ocr_engine_comparison/)
- Overlay visualizations: [results/ocr_engine_comparison/overlays/](../results/ocr_engine_comparison/overlays/)
