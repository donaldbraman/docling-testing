# Abstract-Only Pairs Cleanup Report

**Date:** /Users/donaldbraman/Documents/GitHub/docling-testing

## Summary

- Archived HTML files: 388
- Archived PDF files: 159
- Remaining HTML files: 122
- Remaining PDF files: 95
- arXiv HTML preserved: 38
- arXiv PDF preserved: 48

## Why These Were Archived

These HTML files contained only abstracts and metadata, not full article text. They had very low Jaccard similarity scores (~2-30%) with their corresponding PDFs because they lacked the article body content.

## Restoration

To restore these files, move them back from `data/archived_abstract_only/` to `data/raw_html/` and `data/raw_pdf/`.
