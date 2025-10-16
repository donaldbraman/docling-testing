# Cover Page Platform Analysis Report

Generated: 2025-10-16 18:16:50

## Summary Statistics

- **Total PDFs Processed:** 214
- **Successfully Extracted:** 213 (99%)
- **Failed:** 1

## Platform Distribution

- **Heinonline:** 91 (42%)
- **Publisher_Direct:** 70 (32%)
- **Proquest:** 11 (5%)


## Page Type Classification

Pages were classified into the following categories:

- `platform_header`: Publisher/platform branding (HeinOnline, JSTOR, etc.)
- `institutional_access`: University library metadata/access page
- `article_titlepage`: Article title + author names + affiliation (TRUE COVER)
- `article_abstract`: Abstract or introduction text
- `article_body`: Body text (article has begun)
- `metadata_only`: Version info, archival timestamp
- `unknown`: Could not determine

## Key Findings

1. Platform signatures were automatically detected from text extraction
2. Article cover pages identified where title/author information is present
3. High-confidence matches show clear platform markers

## Next Steps

1. Manual verification of classification (sample review of 30-50 PDFs)
2. Curation of training data from verified article cover pages
3. Document any unusual patterns or edge cases discovered

## Technical Details

- Extraction method: PyPDF text extraction
- Platform detection: Keyword and regex pattern matching
- Generated: 2025-10-16T18:16:50.445782
