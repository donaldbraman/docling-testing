# [ARTICLE BASENAME] - Mismatch Analysis

**Date**: [DATE]
**Investigator**: Claude Code (Autonomous Analysis)
**Total Corrections**: [X]

---

## Summary

- **fn→body corrections**: [X] (gaining body text samples)
- **body→fn corrections**: [X] (preventing RAG contamination)
- **Severity**: [Low / Moderate / High / Critical]
- **Root cause identified**: [Yes / Partial / No]

---

## Investigation Process

### 1. CSV Review
[What patterns were visible in the CSV?]
- [Clustering by page?]
- [Match confidence distribution?]
- [Text patterns?]

### 2. PDF Inspection
**Footnote formatting**:
- [Numbered? Superscript? Position?]

**Layout**:
- [Single/multi-column, quality, etc.]

**Citation style**:
- [Bluebook? Journal-specific?]

### 3. HTML Validation
**Quality**: ✅ Clean / ⚠️ Issues found

**Issues identified**:
- [Inline footnotes?]
- [Contamination?]
- [Missing content?]

### 4. Docling Analysis
**Label distribution**:
```
text: [X]
footnote: [X]
list_item: [X]
section_header: [X]
```

**What Docling got right**:
- [List successes]

**What Docling missed**:
- [List failures]

### 5. Internet Research
[Any journal-specific conventions found?]
[Relevant citation style guides?]

---

## Root Cause Analysis

**Primary issue**: [Describe the main problem]

**Contributing factors**:
1. [Factor 1]
2. [Factor 2]

**Pattern description**:
[Detailed explanation of the systematic pattern]

---

## Example Corrections

### High-Confidence Examples (95%+)

**Example 1**:
- **Original label**: [label]
- **Corrected label**: [label]
- **Confidence**: [X]%
- **Text**: [excerpt]
- **Why mislabeled**: [explanation]

**Example 2**:
[...]

### Medium-Confidence Examples (80-94%)

[Similar format]

---

## HTML Extraction Assessment

**Status**: [No action needed / Needs fixing / Already fixed]

**Specific issues**:
- [Issue 1]
- [Issue 2]

**Recommended fixes**:
- [Fix 1]
- [Fix 2]

---

## Training Signal Quality

**High-confidence corrections suitable for training**: [X] / [total]

**Confidence distribution**:
- 95-100%: [X] corrections
- 85-94%: [X] corrections
- 70-84%: [X] corrections
- <70%: [X] corrections (exclude from training)

**Recommended for training**: ✅ Yes / ⚠️ Partial / ❌ No

**Special considerations**:
- [Any special handling needed?]

---

## Patterns Identified

### Systematic Patterns
1. **[Pattern name]**
   - Description: [...]
   - Frequency: [X] occurrences
   - Example: [...]

2. **[Pattern name]**
   - [...]

### Random/Noise Patterns
- [List any one-off errors]

---

## Recommendations

### Immediate Actions
1. [Action item 1]
2. [Action item 2]

### For Fine-Tuning
- [Should these corrections be used for training?]
- [What would training teach Docling?]
- [Expected improvement?]

### For Validation Set
- [Include in validation set?]
- [Why / why not?]

---

## Cross-Article Insights

[How does this article compare to others?]
[Any unique patterns vs universal patterns?]

---

## Appendix: Raw Stats

**Docling extraction**:
- Total text items: [X]
- Pages: [X]
- Labels: [distribution]

**HTML ground truth**:
- Body paragraphs: [X]
- Footnote paragraphs: [X]
- Total words: [X]

**Disagreement details**:
- [Additional statistics]

---

**Investigation Status**: ✅ Complete / 🔄 In Progress / ⏸️ Paused
**Next Steps**: [What should be done next?]
