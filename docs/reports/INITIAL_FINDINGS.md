# Docling Initial Test Results

**Date:** 2025-10-13
**Test Corpus:** 3 law review articles (Nedrud 1964, Jackson 2014, Green & Roiphe 2020)
**Hardware:** MacBook Pro M3 Max with MPS acceleration

---

## Speed Performance

| Document | Size | Processing Time | Speed |
|----------|------|-----------------|-------|
| Green_Roiphe_2020 | 3.0 MB | 129s | ~2 min |
| Jackson_2014 | 6.6 MB | 197s | ~3 min |
| Nedrud_1964 | 1.9 MB | 77s | ~1 min |
| **Average** | — | **134s** | **~2 min** |

**Comparison:**
- Your spatial detector: ~9 seconds
- Gemini Flash API: ~5-10 seconds
- **Docling: ~2 minutes (15-25x slower)**

---

## Text Quality Issues

### Hyphenation Artifacts

**Total found:** 47 line-break hyphens across 3 documents

- Green_Roiphe: 2 artifacts
- Jackson: 34 artifacts (worst)
- Nedrud: 11 artifacts

**Conclusion:** Docling does NOT fix hyphenation. Still need Flash cleanup pass (~$0.02/doc).

### Footnote Handling

**Critical finding:** Footnotes ARE present in markdown output, but word "footnote" appears 0 times.

**What this means:**
- Either footnotes are detected but not labeled clearly
- Or footnotes are mixed into body text without distinction

**Layout inspection running** to answer: Can we programmatically identify and filter footnotes?

---

## Output Quality

### What's Included (Good and Bad)

✅ Full text extracted
✅ Multi-column layout handled
✅ Reading order preserved
✅ Images marked with `<!-- image -->`

❌ HeinOnline metadata included (citation info header)
❌ Footnotes present in output
❌ Some formatting artifacts ("GLYPH<10>")
❌ Hyphenation not fixed

### Sample Output Structure

```markdown
<!-- image -->

## DATE DOWNLOADED: Sat Sep  6 15:23:30 2025

SOURCE: Content Downloaded from HeinOnline

[Citation information block]

## WHEN PROSECUTORS POLITICK: PROGRESSIVE LAW ENFORCERS THEN AND NOW

[Article body with footnotes interspersed]

1 Mark Berman, These Prosecutors Won Office...
2 Bruce Green & Ellen Yaroshefsky...
```

---

## Key Questions (Pending Layout Inspection)

1. **Can Docling identify footnotes as separate elements?**
   - If YES → We can filter them programmatically
   - If NO → Need custom detection or Flash cleanup

2. **Can it distinguish headers/footers?**
   - Important for removing page metadata

3. **What labels does it assign?**
   - title, text, table, footnote, caption, etc.

4. **Can we access structured data (not just markdown)?**
   - DoclingDocument API for programmatic filtering

---

## Preliminary Assessment

### Pros
- ✅ Works locally (no API costs)
- ✅ Handles complex law review layouts
- ✅ Full text extraction with good fidelity
- ✅ Open source, customizable

### Cons
- ❌ **15-25x slower than alternatives**
- ❌ Footnotes not removed (unlike MinerU)
- ❌ Hyphenation artifacts remain
- ❌ Includes metadata/headers
- ❌ Still need Flash cleanup ($0.02/doc)

### Cost Analysis

**Docling alone:** $0 (compute only)
**Docling + Flash cleanup:** ~$0.02 per document
**Compare to Gemini Flash:** $0.065 per document

**Savings: ~69%** (same as your current spatial + cleanup approach)

---

## Next Steps

1. ⏳ **Complete layout inspection** (running now)
   - Determine if footnotes can be filtered programmatically

2. **If layout detection is good:**
   - Prototype footnote filtering
   - Test on larger corpus (20-30 articles)
   - Compare quality vs spatial + Gemini

3. **If layout detection is poor:**
   - Docling not suitable for your use case
   - Stick with spatial detection or wait for Gemini 3.0

---

## Bottom Line So Far

**Docling is viable IF** it can identify footnotes as separate elements that we can filter out programmatically.

**Speed is acceptable** for batch overnight processing but not for real-time use.

**Quality is good** but not better than your existing spatial detector + Flash cleanup.

**Main value:** Another fallback option in your hybrid extraction stack.

---

*Layout inspection results pending...*
