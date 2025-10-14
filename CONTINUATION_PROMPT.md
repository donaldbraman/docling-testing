# Docling Testing - Continuation Prompt

**Status:** In progress - footnote filtering partially working, needs refinement
**Date:** 2025-10-13
**Test Document:** Jackson_2014.pdf (6.6 MB, 83 pages, law review article)

---

## What We've Accomplished

### ✅ Successfully Tested Docling Extraction
- Installed Docling in sibling repo `/Users/donaldbraman/Documents/GitHub/docling-testing`
- Tested on Jackson_2014.pdf with multiple scaling factors (1x, 2x, 3x)
- Found that 2x scaling was surprisingly 14% faster than 1x (205s vs 238s)
- Confirmed Docling runs on M1 Pro with MPS acceleration and ocrmac OCR

### ✅ Discovered Layout Detection Capability
- **Critical finding:** Docling DOES label document elements including footnotes
- Labels accessible via `doc.iterate_items()`, NOT `result.pages.predictions`
- Configuration requires `generate_parsed_pages=True` in pipeline options

### ✅ Verified Label Distribution (Jackson_2014.pdf)
```
list_item          272 items
text               261 items
footnote           205 items ✅
section_header      32 items
picture              5 items
document_index       1 item
```

### ✅ Confirmed Deterministic Extraction
- Tested fresh extraction vs saved/parsed DoclingDocument
- Results are byte-for-byte identical
- Safe for caching and batch processing

---

## 🚨 PROBLEM DISCOVERED

**Issue:** Not all footnote-like content is labeled as `footnote`

### The Problem
When filtering by `label == 'footnote'` only, we miss **citation-style footnotes** that are labeled as `list_item`:

**Examples of missed citations:**
```
list_item | 132 S. Ct. 2537 (2012).
list_item | 554 U.S. 570 (2008).
list_item | 471 U.S. 1 (1985).
list_item | 424 U.S. 319 (1976).
list_item | 561 U.S. 1 (2010).
```

**Count:**
- **205 items** labeled as `footnote` ✅
- **~9 short citations** labeled as `list_item` ❌ (missed by current filter)
- **~263 long items** labeled as `list_item` ✅ (legitimate body text)

### Why This Happened
The current filter in `extract_body_only.py` only removes items where:
```python
if 'footnote' in label.lower():
    footnote_parts.append(text)
```

But some footnote citations are labeled as `list_item` instead, so they slip through to the body text output.

---

## Current File Structure

```
docling-testing/
├── CONTINUATION_PROMPT.md (this file)
├── BREAKTHROUGH_FINDINGS.md (initial success report)
├── COMPARISON_FRESH_VS_SAVED.md (determinism verification)
├── SCALING_RESULTS.md (1x, 2x, 3x comparison)
├── README.md (project overview)
│
├── test_corpus/law_reviews/
│   ├── Jackson_2014.pdf (6.6 MB)
│   ├── Nedrud_1964.pdf (1.9 MB)
│   └── Green_Roiphe_2020.pdf (3.0 MB)
│
├── results/
│   ├── body_extraction/
│   │   ├── Jackson_2014_default_all.txt (54,019 words)
│   │   ├── Jackson_2014_default_body_only.txt (45,039 words) ⚠️ contains citations
│   │   └── Jackson_2014_default_footnotes_only.txt (8,980 words)
│   ├── saved_vs_fresh/
│   │   └── Jackson_2014_default_doc.pkl (15 MB pickled DoclingDocument)
│   └── scaling_test/
│       ├── Jackson_2014_scale_1.0x.md
│       ├── Jackson_2014_scale_2.0x.md
│       └── Jackson_2014_scale_3.0x.md
│
└── scripts/
    ├── test_scaling.py (tested 1x, 2x, 3x scaling)
    ├── extract_body_only.py (current filter - NEEDS FIX)
    ├── parse_saved_result.py (tested determinism)
    ├── inspect_boxes.py (explored data structures)
    ├── check_numbered_labels.py (diagnostic)
    └── analyze_list_items.py (categorization analysis)
```

---

## Next Steps to Fix the Problem

### 1. Improve Citation Detection Heuristic

Update `extract_body_only.py` to detect citation-style list items:

```python
import re

def is_likely_citation(text: str) -> bool:
    """Detect if a list_item is actually a footnote citation."""
    text = text.strip()

    # Short items with case citations: "132 S. Ct. 2537 (2012)"
    if len(text) < 100 and re.match(r'^\d+.*\d+.*\(.*\d{4}.*\)', text[:60]):
        return True

    # Items that start with "See" or "Id." (common citation patterns)
    if len(text) < 150 and re.match(r'^(See|Id\.|Ibid\.)', text):
        return True

    return False

# Then in filtering loop:
for item, level in doc.iterate_items():
    label = str(item.label)
    text = item.text

    if text:
        if 'footnote' in label.lower():
            footnote_parts.append(text)
        elif label.lower() == 'list_item' and is_likely_citation(text):
            footnote_parts.append(text)  # Treat as footnote
        elif label.lower() in ['text', 'section_header', 'list_item', 'paragraph']:
            body_text_parts.append(text)
```

### 2. Test the Improved Filter

Run extraction with updated heuristic and verify:
- Are the 9 short citations now removed?
- Are the 263 long list items still included in body text?
- What's the new word count difference?

### 3. Manual Verification

Compare outputs:
```bash
cd /Users/donaldbraman/Documents/GitHub/docling-testing
diff results/body_extraction/Jackson_2014_default_body_only.txt \
     results/body_extraction/Jackson_2014_improved_body_only.txt
```

Check that only citation-style items were removed.

### 4. Test on Additional Documents

Once the filter works well on Jackson_2014.pdf, test on:
- Nedrud_1964.pdf (older article, different formatting)
- Green_Roiphe_2020.pdf (modern article)

Verify the heuristic works across different law review styles.

---

## Alternative Approaches to Consider

### Option A: Pattern-Based Detection (Current)
**Pros:** Fast, no additional dependencies
**Cons:** May need tuning per document style

### Option B: Use Docling's "Figure" or "Table" Labels
Check if citations might also be labeled as other types we haven't examined yet.

### Option C: Post-Process with Gemini Flash
Send the "body_only" output to Gemini Flash with prompt:
```
Remove any remaining legal citations, case references, or footnote-style
content from this academic text. Preserve only the main body text.
```
**Cost:** ~$0.02 per document
**Benefit:** More robust across different document styles

### Option D: Train Custom Citation Detector
Use the 205 correctly-labeled footnotes as training data to build a classifier for the edge cases.

---

## Key Configuration Details

### Working Docling Configuration
```python
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    TableFormerMode,
    LayoutOptions,
)

pipeline = PdfPipelineOptions(
    layout_options=LayoutOptions(),
    generate_parsed_pages=True,  # CRITICAL for labels
    generate_page_images=True,
    images_scale=1.0,  # Or 2.0 for better detection
    do_table_structure=True,
    table_structure_options=dict(
        mode=TableFormerMode.ACCURATE,
        do_cell_matching=False,
    ),
    do_ocr=True,
)
```

### How to Access Labels
```python
result = converter.convert(str(pdf_path))
doc = result.document

for item, level in doc.iterate_items():
    label = str(item.label)  # 'footnote', 'text', 'list_item', etc.
    text = item.text
```

---

## Performance Metrics (Current)

| Metric | Value |
|--------|-------|
| **Extraction time** | ~3-4 minutes per document |
| **Footnotes detected** | 205 (labeled as 'footnote') |
| **Citations missed** | ~9 (labeled as 'list_item') |
| **Total removed** | 8,980 words (16.6% of total) |
| **Body text** | 45,039 words |
| **Hyphenation artifacts** | 29 remaining |

---

## Cost Analysis

### Current Approach: Docling + Flash Cleanup
1. **Docling extraction:** $0 (local, ~3 min)
2. **Flash hyphenation fix:** $0.02 (5-10 sec)
3. **Total:** $0.02 per document

### Alternative: Pure Gemini
- **Flash:** $0.065 per document
- **Pro:** $0.26 per document

**Savings with Docling:** 69% vs Flash, 92% vs Pro

---

## Questions to Answer

1. **Citation detection accuracy:** What heuristic catches all citation-style list_items without false positives?

2. **Cross-document robustness:** Does the same heuristic work on articles from different law reviews, different eras?

3. **Cost-benefit trade-off:** Is the added complexity of heuristic detection worth the 69% cost savings vs just using Gemini Flash?

4. **Quality comparison:** How does Docling + improved filter + Flash cleanup compare to pure Gemini Pro quality?

5. **Integration path:** If we proceed, how should this integrate into the cite-assist pipeline?

---

## Commands to Resume Work

### Check current extraction quality
```bash
cd /Users/donaldbraman/Documents/GitHub/docling-testing
grep -n "^\d\+\. .*U\.S\." results/body_extraction/Jackson_2014_default_body_only.txt | head -20
```

### Re-run extraction with improved filter
```bash
cd /Users/donaldbraman/Documents/GitHub/docling-testing
uv run python extract_body_only_improved.py  # After creating this script
```

### Compare outputs
```bash
diff results/body_extraction/Jackson_2014_default_body_only.txt \
     results/body_extraction/Jackson_2014_improved_body_only.txt
```

---

## Immediate Next Action

**Update `extract_body_only.py` with improved citation detection heuristic and re-run extraction on Jackson_2014.pdf**

This will tell us if the heuristic approach is viable or if we need to consider alternatives (post-processing with Gemini, custom ML model, etc.).

---

## Context for AI Assistant

When resuming this work, the key question is:

> **Can we reliably distinguish citation-style list_items from legitimate body text list_items using pattern matching, or do we need a more sophisticated approach?**

Current hypothesis: Short list_items (<100 chars) matching legal citation patterns are likely footnotes, while longer list_items are legitimate body content.

Test this hypothesis and report results.
