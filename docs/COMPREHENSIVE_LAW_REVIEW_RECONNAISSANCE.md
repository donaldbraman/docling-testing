# Comprehensive Law Review Reconnaissance Report

**Date:** 2025-10-17
**Assessed:** 21 top law reviews (excluding those already in corpus)
**Method:** Parallel agent reconnaissance with website sampling

## Executive Summary

**Full-text HTML Available:** 1 journal (4.8%)
**Partial/Mixed:** 1 journal (4.8%)
**Abstract-only:** 19 journals (90.4%)

**Recommendation:** The overwhelming majority of top law reviews use abstract-only websites. Focus collection efforts on the **one confirmed full-text source** (Michigan Law Review) and consider alternative strategies.

## Results by Category

### ✅ FULL-TEXT HTML (1 journal)

#### Michigan Law Review ⭐
- **Website:** https://michiganlawreview.org
- **Word count:** 8,750-17,000 words per article
- **Status:** Complete article text with full sections, footnotes
- **Collection script:** `scripts/data_collection/scrape_michigan.py`
- **Recommendation:** **HIGH PRIORITY - COLLECT IMMEDIATELY**

### 🟡 PARTIAL/MIXED (1 journal)

#### Washington University Law Review
- **Website:** https://wustllawreview.org/
- **Traditional articles:** Abstract-only (skip)
- **Online Essays:** Full-text HTML (~8,500-9,000 words)
- **Note:** Online essays are shorter form, but full-text
- **Recommendation:** **CONSIDER** - Smaller volume but usable

### ❌ ABSTRACT-ONLY (19 journals)

#### Top 14 Law Schools - All Abstract-Only
1. **Yale Law Journal** - https://www.yalelawjournal.org
   - Extended abstracts (3,000-7,000 words) but not full articles

2. **Stanford Law Review** - https://www.stanfordlawreview.org/
   - Landing pages with 400-500 word abstracts

3. **Harvard Law Review** *(already assessed previously)*
   - Limited full-text availability

4. **Columbia Law Review** - https://columbialawreview.org
   - Extended introductions (800-4,000 words) only

5. **NYU Law Review** - https://nyulawreview.org/
   - 180-300 word abstracts only

6. **University of Pennsylvania Law Review** - https://scholarship.law.upenn.edu/penn_law_review/
   - Digital Commons repository, 250-300 word abstracts

7. **Virginia Law Review** - https://www.virginialawreview.org/
   - 2,800-3,000 word introductions only

8. **Duke Law Journal** - https://scholarship.law.duke.edu/dlj/
   - bePress repository, 100-350 word abstracts

9. **Northwestern Law Review** - https://northwesternlawreview.org
   - 150-500 word abstracts

10. **Cornell Law Review** - https://scholarship.law.cornell.edu/clr/
    - Metadata only, no abstracts visible

11. **Georgetown Law Journal** - https://www.law.georgetown.edu/georgetown-law-journal/
    - 80-450 word abstracts

12. **UCLA Law Review** - https://www.uclalawreview.org/
    - 300-500 word abstracts, PDFs not linked

13. **Vanderbilt Law Review** - https://scholarship.law.vanderbilt.edu/vlr/
    - Digital Commons, 200-250 word abstracts

14. **University of Chicago Law Review** *(already in corpus)*
    - 2 pairs already collected

#### Other Top 50 - All Abstract-Only

15. **Minnesota Law Review** - https://minnesotalawreview.org/
    - 150-250 word abstracts

16. **Iowa Law Review** - https://ilr.law.uiowa.edu/
    - 250-400 word abstracts

17. **Notre Dame Law Review** - https://scholarship.law.nd.edu/ndlr/
    - bePress repository, 150-350 word abstracts

18. **Emory Law Journal** - https://scholarlycommons.law.emory.edu/elj/
    - Digital Commons, 800-900 word abstracts

19. **GWU Law Review** - https://www.gwlr.org/
    - 200-250 word abstracts, PDFs on volume pages

20. **Fordham Law Review** - https://ir.lawnet.fordham.edu/flr/
    - bePress repository, 400-600 word abstracts

21. **Indiana Law Journal** *(assessed in first batch)*
    - 150-300 word abstracts

## Analysis

### Platform Distribution

**Abstract-only platforms used:**
- **bePress Digital Commons:** 8 journals (Duke, Cornell, Vanderbilt, Notre Dame, Emory, Penn, Fordham)
- **Custom CMS with abstract landing pages:** 11 journals (Yale, Stanford, Columbia, NYU, Virginia, Northwestern, Georgetown, UCLA, Minnesota, Iowa, GWU)
- **Full-text HTML platform:** 1 journal (Michigan)
- **Mixed platform:** 1 journal (WashU)

### Key Insight

**90.4% of top law reviews are abstract-only.** This represents a fundamental structural challenge with law review data collection. The legal academic publishing model favors:
- PDF as primary distribution format
- Website as discovery/metadata layer
- Database partnerships (Westlaw, Lexis, HeinOnline) for full-text access

### Comparison to Current Corpus

**Journals already well-represented (skip these):**
- Texas Law Review: 11 pairs
- California Law Review: 10 pairs
- USC Law Review: 9 pairs
- Boston University Law Review: 3 pairs
- University of Chicago Law Review: 2 pairs
- Harvard Law Review: 1 pair
- Wisconsin Law Review: 1 pair

**Total current sources:** 7 journals (37 law review pairs)

**Potential new sources from reconnaissance:**
- Michigan Law Review: Full-text ✅
- Washington University (online essays): Partial ⚠️

## Recommendations

### Immediate Action

**1. Collect from Michigan Law Review**
- Use: `scripts/data_collection/scrape_michigan.py`
- Target: 8-10 high-quality pairs
- Expected quality: ≥75% Jaccard (full-text HTML)
- Timeline: Can be done immediately

**2. Optionally collect WashU Online Essays**
- Manual collection needed (different from traditional articles)
- Smaller volume but high quality
- Target: 3-5 essays if available

### Strategic Pivot

Given the 90.4% failure rate, consider:

**Option A: Focus on existing corpus quality**
- Current 37 law review pairs have 91.3% average Jaccard
- Combined with 38 arXiv pairs = 75 high-quality pairs total
- May be sufficient for initial DoclingBERT v3 training

**Option B: Expand to alternative sources**
- More arXiv papers (guaranteed full-text)
- Government documents (regulations, court opinions)
- Open-access journals in other fields
- Academic repositories with full-text HTML

**Option C: Hybrid approach**
- Collect Michigan (adds 8th journal)
- Collect more from existing full-text sources (California, Texas, USC)
- Supplement with arXiv to reach target corpus size

### Updated Corpus Projection

**If we collect Michigan Law Review:**
- Total journals: 8
- Total law review pairs: ~45-47
- Combined with arXiv: ~83-85 total pairs
- Diversity: Good (8 different top-tier journals)

**Recommended target:** 80-100 high-quality pairs total
- Current: 75 pairs (37 law + 38 arXiv)
- Add Michigan: +8-10 = 83-85 pairs
- Gap to 100: Need 15-25 more pairs

**To reach 100 pairs:**
- Collect Michigan: +8-10
- Collect more arXiv: +10-15
- **OR** collect more from existing sources (California has 18 available full-text HTML files per categorization)

## Technical Findings

### Abstract-Only Indicators
Agents identified these common patterns:
- Prominent "Download PDF" buttons
- Short word counts (<1,000 words on page)
- Metadata focus (author, citation, keywords)
- Database links (Westlaw, Lexis, HeinOnline)
- Repository platforms (bePress, Digital Commons)

### Full-Text Indicators
- Long word counts (8,000+ words)
- Multiple sections visible
- Integrated footnotes in HTML
- Navigation within article (table of contents)
- No prominent PDF download button

## Next Steps

**Decision point for user:**

1. **Immediate collection?**
   - Deploy agent to collect Michigan Law Review (8-10 pairs)
   - Timeline: 2-3 hours

2. **Expand reconnaissance?**
   - Assess remaining top 100 (non-T14) law reviews
   - May find 1-2 more full-text sources

3. **Pivot to alternatives?**
   - Focus on arXiv expansion
   - Explore other academic fields

4. **Proceed with training?**
   - Current 75 pairs may be sufficient
   - Focus on corpus v3 rebuild with existing data

## Conclusion

**Reality check:** Only 1 out of 21 top law reviews (4.8%) provides full-text HTML suitable for our collection method. This validates our earlier findings and suggests that law review data collection via HTML scraping is fundamentally limited by the publishing model used by legal academic journals.

**Recommended path forward:** Collect Michigan Law Review to add diversity (8th journal), then proceed with corpus v3 training using the resulting ~85 high-quality pairs.

---

*Generated: 2025-10-17*
*Reconnaissance: 21 journals assessed via parallel agents*
*Success rate: 4.8% full-text HTML availability*
