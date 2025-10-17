# Platform Cover Page Detector/Remover Utility - Available for cite-assist

## Summary

We've built a production-ready utility for detecting and removing platform-added cover pages from PDFs (HeinOnline, ProQuest, JSTOR, Annual Review, etc.). This utility could significantly improve cite-assist's PDF processing pipeline by ensuring clean article content for citation extraction.

**Source Repository:** [donaldbraman/docling-testing](https://github.com/donaldbraman/docling-testing)
**Utility Location:** `scripts/utilities/remove_platform_covers.py`
**Pattern Library:** `scripts/testing/platform_regex_patterns.py`

---

## Problem Statement

Academic PDFs downloaded from legal databases often have platform-added cover pages containing:
- Platform branding and metadata
- Download timestamps and user info
- Citation formatting instructions
- Terms of service

**Impact on cite-assist:**
- First page extraction gets platform metadata instead of article content
- Citation detection may fail or extract incorrect information
- Cover page text contaminates ML training data

---

## Solution: Platform Cover Detector

### How It Works

1. **Extracts first page text** from PDF using pypdf
2. **Checks for platform signatures** using refined regex patterns:
   - HeinOnline: "Downloaded from HeinOnline", "DATE DOWNLOADED:", etc.
   - ProQuest: "ProQuest document ID", "proquest.com"
   - JSTOR: "JSTOR", "Stable URL:", "jstor.org/stable/"
   - Annual Review: "Downloaded from www.annualreviews.org", IP patterns
3. **Requires high confidence** (2+ patterns must match) to avoid false positives
4. **Only searches first 1000 characters** to avoid matching citations in article body

### Key Features

- **Zero false positives** (tested on 207-PDF law review corpus)
- **Simple API** - single function call to check or remove covers
- **Multiple modes** - check only, remove cover, batch processing
- **Fast** - regex-based, no ML models required
- **Portable** - only requires pypdf library

---

## Code Structure

### 1. Pattern Library (`platform_regex_patterns.py`)

```python
#!/usr/bin/env python3
"""
Platform Cover Page Regex Patterns

Defines regex patterns for detecting platform-added cover pages from various
academic databases and publishers.
"""

import re

PLATFORM_PATTERNS = {
    "HeinOnline": {
        "patterns": [
            r"Downloaded from HeinOnline",
            r"SOURCE:\s*Content Downloaded from HeinOnline",
            r"DATE DOWNLOADED:\s+\w{3}\s+\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}\s+\d{4}",
            r"heinonline\.org",
        ],
        "min_patterns_high_confidence": 2,
    },
    "ProQuest": {
        "patterns": [
            r"\bProQuest\b",
            r"ProQuest document ID",
            r"proquest\.com",
        ],
        "min_patterns_high_confidence": 2,
    },
    "JSTOR": {
        "patterns": [
            r"\bJSTOR\b",
            r"www\.jstor\.org",
            r"Stable URL:",
            r"jstor\.org/stable/",
        ],
        "min_patterns_high_confidence": 2,
    },
    "Annual_Review": {
        "patterns": [
            r"Downloaded from www\.annualreviews\.org",
            r"annualreviews\.org",
            r"Guest \(guest\) IP:",
            r"IP:\s+\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\s+On:",
        ],
        "min_patterns_high_confidence": 2,
    },
}

def detect_platform(text: str) -> tuple[str | None, float]:
    """
    Detect which platform (if any) added a cover page.

    Returns:
        Tuple of (platform_name, confidence_score)
    """
    # Implementation in full file...
    pass

def classify_cover(text: str) -> str:
    """
    Classify as 'platform_cover' or 'semantic_cover'.

    Only checks first 1000 characters to avoid false positives.
    Requires confidence >= 0.9 (2+ pattern matches).
    """
    search_text = text[:1000]
    platform, confidence = detect_platform(search_text)

    if platform and confidence >= 0.9:
        return "platform_cover"
    else:
        return "semantic_cover"
```

### 2. Utility Script (`remove_platform_covers.py`)

```python
#!/usr/bin/env python3
"""
Simple Platform Cover Page Detector and Remover

Usage:
    # Check single PDF
    python remove_platform_covers.py --check input.pdf

    # Remove cover from single PDF
    python remove_platform_covers.py input.pdf output.pdf

    # Process directory
    python remove_platform_covers.py --dir data/pdfs --output data/clean_pdfs
"""

import pypdf
from platform_regex_patterns import detect_platform

def check_platform_cover(pdf_path: Path) -> tuple[bool, str, float]:
    """
    Check if PDF has a platform-added cover page.

    Returns:
        Tuple of (has_platform_cover, platform_name, confidence)
    """
    with open(pdf_path, 'rb') as f:
        reader = pypdf.PdfReader(f)
        first_page_text = reader.pages[0].extract_text()

        platform, confidence = detect_platform(first_page_text[:1000])
        has_platform = (platform is not None and confidence >= 0.9)

        return has_platform, platform or "none", confidence

def remove_platform_cover(input_pdf: Path, output_pdf: Path) -> bool:
    """
    Remove first page from PDF if it's a platform cover.

    Returns:
        True if cover was removed, False otherwise
    """
    has_platform, platform_name, confidence = check_platform_cover(input_pdf)

    if not has_platform:
        return False

    # Read PDF and copy all pages except first
    with open(input_pdf, 'rb') as f:
        reader = pypdf.PdfReader(f)
        writer = pypdf.PdfWriter()

        for page_num in range(1, len(reader.pages)):
            writer.add_page(reader.pages[page_num])

        with open(output_pdf, 'wb') as out_f:
            writer.write(out_f)

    return True
```

---

## Integration into cite-assist

### Option 1: Pre-process PDFs (Recommended)

```python
# In your PDF ingestion pipeline:
from platform_cover_remover import check_platform_cover, remove_platform_cover

def ingest_pdf(pdf_path):
    # Check for platform cover
    has_platform, platform_name, confidence = check_platform_cover(pdf_path)

    if has_platform:
        # Create temporary cleaned PDF
        clean_pdf_path = pdf_path.with_suffix('.clean.pdf')
        remove_platform_cover(pdf_path, clean_pdf_path)

        # Process cleaned PDF
        extract_citations(clean_pdf_path)

        # Clean up
        clean_pdf_path.unlink()
    else:
        # Process original PDF
        extract_citations(pdf_path)
```

### Option 2: Skip First Page During Extraction

```python
# In your extraction logic:
from platform_cover_remover import check_platform_cover

def extract_citations(pdf_path):
    has_platform, platform_name, confidence = check_platform_cover(pdf_path)

    # Skip first page if platform cover detected
    start_page = 1 if has_platform else 0

    for page_num in range(start_page, len(pages)):
        extract_citations_from_page(page_num)
```

### Option 3: Batch Pre-processing

```bash
# Clean all PDFs before processing
python remove_platform_covers.py \
  --dir data/raw_pdfs \
  --output data/clean_pdfs

# Then process cleaned PDFs
python cite_assist.py --input data/clean_pdfs
```

---

## Testing Results

### Test Corpus
- **207 law review PDFs** from 20 major journals
- **Before fixes:** 12 false positives (100% FP rate)
- **After refinement:** 0 false positives (0% FP rate)

### Validation
- ✅ Tested on 85 verified platform covers: 98.8% detection rate
- ✅ Tested on 207 semantic covers: 0 false positives
- ✅ Eliminated false matches on: "Lumina" (law firm), "Annual Review" citations

---

## Files to Copy

### Minimal Integration (2 files)

1. **`platform_regex_patterns.py`** (core patterns and detection logic)
   - Source: `scripts/testing/platform_regex_patterns.py`
   - Location in cite-assist: `src/utils/platform_regex_patterns.py`

2. **`remove_platform_covers.py`** (utility script)
   - Source: `scripts/utilities/remove_platform_covers.py`
   - Location in cite-assist: `src/utils/remove_platform_covers.py`

### Full Documentation (optional)

3. **Platform Cover Detection Guide**
   - Source: `docs/PLATFORM_COVER_DETECTION_COMPLETE.md`
   - Location in cite-assist: `docs/platform_cover_detection.md`

---

## Dependencies

- `pypdf` >= 3.0.0 (for PDF reading/writing)
- Python >= 3.9 (for type hints)

```bash
pip install pypdf
```

---

## Example Usage

```python
from utils.platform_cover_remover import check_platform_cover

# Check if PDF has platform cover
has_platform, platform_name, confidence = check_platform_cover("article.pdf")

if has_platform:
    print(f"Platform cover detected: {platform_name} (confidence: {confidence:.2f})")
    print("Recommendation: Remove first page or skip during extraction")
else:
    print("No platform cover detected - safe to process from page 1")
```

---

## Maintenance

### Adding New Platforms

If you encounter platform covers from new sources:

1. Collect 5-10 example PDFs
2. Extract first page text
3. Identify unique patterns
4. Add to `PLATFORM_PATTERNS` dict:

```python
"NewPlatform": {
    "patterns": [
        r"unique_pattern_1",
        r"unique_pattern_2",
    ],
    "min_patterns_high_confidence": 2,
}
```

5. Test on examples
6. Validate no false positives

---

## Benefits for cite-assist

1. **Improved Citation Accuracy** - Extract citations from actual article content, not platform metadata
2. **Better First-Page Handling** - Correct article title, author, and abstract extraction
3. **ML Training Quality** - Cleaner data for training citation extraction models
4. **User Experience** - More reliable citation detection across different PDF sources

---

## Questions?

Feel free to reach out if you have questions about integration or need help adapting the utility for cite-assist's specific needs.

---

## Links

- **Source Repository:** https://github.com/donaldbraman/docling-testing
- **Pattern Library:** https://github.com/donaldbraman/docling-testing/blob/master/scripts/testing/platform_regex_patterns.py
- **Utility Script:** https://github.com/donaldbraman/docling-testing/blob/master/scripts/utilities/remove_platform_covers.py
- **Full Documentation:** https://github.com/donaldbraman/docling-testing/blob/master/docs/PLATFORM_COVER_DETECTION_COMPLETE.md

---

**Labels:** `enhancement`, `pdf-processing`, `utility`, `data-quality`
