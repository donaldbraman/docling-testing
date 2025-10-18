# Law Review Website Reconnaissance Report

**Date:** 2025-10-17
**Purpose:** Assess underrepresented law reviews for full-text HTML availability

## Summary

**Assessed:** 6 underrepresented law reviews
**Full-text HTML:** 1 (16.7%)
**Abstract-only:** 5 (83.3%)

## Results

### ✅ COLLECT - Full-Text HTML Available

#### Michigan Law Review
- **Website:** https://michiganlawreview.org
- **Status:** FULL-TEXT ✅
- **Word count:** 8,750 - 17,000 words per article
- **Evidence:** Complete article text with full section structure (Introduction, Parts I-III, Conclusion, footnotes)
- **Sample articles checked:** 3
- **Recommendation:** **COLLECT** - Excellent candidate for corpus

### ❌ SKIP - Abstract-Only

#### Stanford Law Review
- **Website:** https://www.stanfordlawreview.org/
- **Status:** ABSTRACT-ONLY
- **Word count:** 400-500 words (abstract only)
- **Evidence:** Landing pages with abstracts, metadata, PDF download links only
- **Recommendation:** SKIP

#### Columbia Law Review
- **Website:** https://columbialawreview.org
- **Status:** ABSTRACT-ONLY
- **Word count:** 800-4,000 words (extended abstracts/introductions)
- **Evidence:** Introductory content only, requires PDF download for full text
- **Recommendation:** SKIP

#### Virginia Law Review
- **Website:** https://www.virginialawreview.org/
- **Status:** ABSTRACT-ONLY
- **Word count:** 2,800-3,000 words (introduction only)
- **Evidence:** Extended abstracts/introductions, full text via PDF/databases only
- **Recommendation:** SKIP

#### Northwestern Law Review
- **Website:** https://northwesternlawreview.org
- **Status:** ABSTRACT-ONLY
- **Word count:** 150-500 words (abstract only)
- **Evidence:** Metadata/abstract repositories with PDF downloads
- **Recommendation:** SKIP

#### Indiana Law Journal
- **Website:** https://www.repository.law.indiana.edu/ilj/
- **Status:** ABSTRACT-ONLY
- **Word count:** 150-300 words (abstract only)
- **Evidence:** Digital repository with abstracts and PDF downloads only
- **Recommendation:** SKIP

## Analysis

### Key Finding

**Only 16.7% of assessed law reviews provide full-text HTML** - This validates our previous discovery that most law review websites serve as abstract/metadata portals rather than full-text platforms.

### Pattern Identified

**Abstract-only characteristics:**
- Prominent "Download PDF" buttons
- Short word counts (150-4,000 words)
- Metadata-focused layout
- Database links (Westlaw, Lexis, HeinOnline)
- Repository/landing page structure

**Full-text characteristics:**
- Long word counts (8,000+ words)
- Complete section structure
- Multiple parts/subsections
- Integrated footnotes
- Article navigation within page

## Recommendations

### Immediate Action

**Collect from Michigan Law Review:**
- Use existing script: `scripts/data_collection/scrape_michigan.py`
- Target: 8-10 high-quality pairs
- Expected quality: ≥75% Jaccard similarity (based on full-text HTML)

### Future Reconnaissance Needed

Check these additional sources for underrepresented journals:
- **Yale Law Journal** - Not yet assessed
- **Penn Law Review** - Have collection script, need assessment
- **Duke Law Journal** - Have collection script, need assessment
- **Georgetown Law Journal** - Have collection script, need assessment

### Long-term Strategy

Given the low hit rate (16.7%), we should:
1. **Prioritize journals with known full-text HTML:**
   - California Law Review (already well-represented)
   - Texas Law Review (already well-represented)
   - USC Law Review (already well-represented)
   - Michigan Law Review (NEW - priority target)

2. **Focus on quality over quantity:**
   - Better to have 37 excellent pairs than 200 poor ones
   - Our current 37 pairs (91.3% avg Jaccard) are high quality

3. **Consider alternative sources:**
   - More arXiv papers (confirmed full-text)
   - Other open-access journals with HTML
   - Government/court documents with structured HTML

## Impact on Corpus Goals

**Current high-quality corpus:** 37 law review pairs + 38 arXiv = 75 total

**If we collect from Michigan:**
- Target: +8-10 pairs
- New total: ~83-85 pairs
- Diversity improvement: Add Michigan to our 4 current journals

**Revised diversity:**
- Texas: 11 pairs (13.3%)
- California: 10 pairs (12.0%)
- USC: 9 pairs (10.8%)
- **Michigan: 8-10 pairs (9.6-12.0%)** ← NEW
- BU: 3 pairs (3.6%)
- Chicago: 2 pairs (2.4%)
- Harvard: 1 pair (1.2%)
- Wisconsin: 1 pair (1.2%)

This would give us **8 different law reviews** with reasonable distribution.

## Next Steps

1. ✅ **Reconnaissance complete** for 6 underrepresented journals
2. **Decision point:** Collect from Michigan Law Review?
3. **Optional:** Assess additional journals (Yale, Penn, Duke, Georgetown)
4. **Alternative:** Focus on corpus v3 training with existing 75 high-quality pairs

---

*Generated: 2025-10-17*
*Reconnaissance agents: 6 parallel assessments completed*
