# Fresh Extraction vs Saved/Parsed Comparison

**Date:** 2025-10-13
**Test Document:** Jackson_2014.pdf (6.6 MB, 83 pages)
**Configuration:** Default (Heron model, 1.0x scaling)

---

## Test Objective

Verify that parsing a saved DoclingDocument produces identical results to parsing during extraction.

**Hypothesis:** Docling extraction is deterministic - parsing the same DoclingDocument object should always produce identical text output.

---

## Test Methodology

### Approach 1: Fresh Extraction
1. Convert PDF → DoclingDocument
2. Parse items and filter during conversion
3. Save body text and footnotes immediately

### Approach 2: Save/Parse
1. Convert PDF → DoclingDocument
2. Pickle the DoclingDocument object to disk
3. Load pickled DoclingDocument
4. Parse items and filter from loaded object
5. Save body text and footnotes

---

## Results

| Metric | Fresh Extraction | Saved/Parsed | Difference |
|--------|-----------------|--------------|------------|
| **Extraction time** | 187.5s (3.1 min) | 213.7s (3.6 min) | 26.2s (normal variation) |
| **Parsing time** | During extraction | Instant | N/A |
| **Footnotes detected** | 205 | 205 | ✅ 0 |
| **Total words** | 54,019 | 54,019 | ✅ 0 |
| **Body text words** | 45,039 | 45,039 | ✅ 0 |
| **Footnote words** | 8,980 | 8,980 | ✅ 0 |
| **Hyphen artifacts (all)** | 34 | 34 | ✅ 0 |
| **Hyphen artifacts (body)** | 29 | 29 | ✅ 0 |
| **Removal rate** | 16.6% | 16.6% | ✅ 0 |

---

## File Comparison

### Body Text Comparison
```bash
$ diff results/body_extraction/Jackson_2014_default_body_only.txt \
       results/saved_vs_fresh/Jackson_2014_default_parsed_body_only.txt
```
**Result:** ✅ **NO DIFFERENCES** - Files are byte-for-byte identical

### Footnotes Comparison
```bash
$ diff results/body_extraction/Jackson_2014_default_footnotes_only.txt \
       results/saved_vs_fresh/Jackson_2014_default_parsed_footnotes_only.txt
```
**Result:** ✅ **NO DIFFERENCES** - Files are byte-for-byte identical

---

## Conclusions

### ✅ Hypothesis Confirmed

**Docling extraction is fully deterministic.**

Parsing a saved DoclingDocument produces **identical** output to parsing during extraction:
- Same footnote detection (205)
- Same word counts
- Same text content (byte-for-byte)
- Same hyphenation artifacts

### Extraction Time Variability

The 26.2-second difference in extraction time (187.5s vs 213.7s) is **normal system variance**:
- Background processes
- CPU thermal throttling
- Memory pressure
- I/O contention

This variability is expected and does NOT affect output determinism.

---

## Practical Implications

### ✅ Can Cache Extracted Documents
Since extraction is deterministic, we can:
1. Extract once → pickle DoclingDocument
2. Parse multiple times from cached pickle
3. Apply different filtering strategies without re-extraction
4. Save ~3 minutes per re-parse

### ✅ Reliable for Production
The deterministic nature of Docling extraction makes it suitable for production use:
- Consistent results across runs
- Reproducible outputs
- Safe for caching and batch processing

### ✅ Testable and Verifiable
Determinism enables:
- Unit testing with fixed expected outputs
- Regression testing
- Quality assurance validation

---

## Performance Characteristics

### Initial Extraction
- **Time:** ~3-4 minutes per document
- **Cost:** $0 (local compute)
- **Quality:** 205/205 footnotes detected

### Subsequent Parsing (from pickle)
- **Time:** Instant (<1 second)
- **Cost:** $0
- **Quality:** Identical to initial extraction

### Storage Cost
- **Pickled DoclingDocument:** ~15 MB for Jackson_2014.pdf
- **Body text:** ~140 KB
- **Footnotes text:** ~40 KB

---

## Recommendation

**Use saved DoclingDocument objects** when:
1. Testing different filtering strategies
2. Applying multiple output formats
3. Iterating on text processing pipelines
4. Quality assurance and validation

**Fresh extraction** when:
1. First-time processing
2. Configuration changes (scaling, model settings)
3. Docling version upgrades

---

## Files Generated

### Fresh Extraction
- `results/body_extraction/Jackson_2014_default_all.txt`
- `results/body_extraction/Jackson_2014_default_body_only.txt`
- `results/body_extraction/Jackson_2014_default_footnotes_only.txt`

### Saved/Parsed
- `results/saved_vs_fresh/Jackson_2014_default_doc.pkl` (15 MB)
- `results/saved_vs_fresh/Jackson_2014_default_parsed_all.txt`
- `results/saved_vs_fresh/Jackson_2014_default_parsed_body_only.txt`
- `results/saved_vs_fresh/Jackson_2014_default_parsed_footnotes_only.txt`

---

## Verified By

```bash
# Byte-for-byte comparison
diff results/body_extraction/Jackson_2014_default_body_only.txt \
     results/saved_vs_fresh/Jackson_2014_default_parsed_body_only.txt
# Exit code: 0 (identical)

diff results/body_extraction/Jackson_2014_default_footnotes_only.txt \
     results/saved_vs_fresh/Jackson_2014_default_parsed_footnotes_only.txt
# Exit code: 0 (identical)
```

**Status:** ✅ **VERIFIED - IDENTICAL OUTPUTS**
