# Corpus Diversity Assessment - HTML-PDF Pairs

**Date:** October 17, 2025
**Analyst:** Claude Code
**Status:** 🔴 CRITICAL - Immediate action required for non-law diversity

---

## Executive Summary

**Law Review Diversity:** ✅ **EXCELLENT** (20 journals, highly balanced)
**Non-Law Diversity:** ❌ **ZERO** (critical overfitting risk)

**Verdict:** Current corpus has excellent diversity WITHIN law reviews but ZERO diversity ACROSS document types. This creates severe overfitting risk for DoclingBERT v3.1.

---

## Part 1: Law Review HTML-PDF Pair Diversity

### Overall Statistics
- **Total matched pairs:** 207
- **Unique law reviews:** 20 journals
- **Geographic regions:** 8 (Mid-Atlantic to West Coast)
- **Diversity score (HHI):** 582 (excellent - below 1500 threshold)

### Distribution Analysis

**Top 10 Law Reviews:**
| Rank | Journal | Pairs | % of Total |
|------|---------|-------|-----------|
| 1 | Wisconsin Law Review | 16 | 7.7% |
| 2 | Florida Law Review | 16 | 7.7% |
| 3 | Northwestern Law Review | 15 | 7.2% |
| 4 | Chicago Law Review | 15 | 7.2% |
| 5 | Texas Law Review | 15 | 7.2% |
| 6 | Stanford Law Review | 14 | 6.8% |
| 7 | Virginia Law Review | 14 | 6.8% |
| 8 | USC Law Review | 12 | 5.8% |
| 9 | Penn Law Review | 12 | 5.8% |
| 10 | GWU Law Review | 11 | 5.3% |

**Key Observations:**
- ✅ No single journal dominates (max 7.7%)
- ✅ Top 3 journals = only 22.7% (very balanced)
- ✅ Top 10 journals = 67.6% (healthy distribution)
- ✅ Bottom 10 journals still contribute 32.4%

### Geographic Diversity

| Region | Pairs | % |
|--------|-------|---|
| Mid-Atlantic (VA, DC, PA) | 47 | 22.7% |
| California (Stanford, UCLA, USC, Berkeley) | 41 | 19.8% |
| Midwest (Chicago, Northwestern, Illinois) | 30 | 14.5% |
| Upper Midwest (Minnesota, Wisconsin, Iowa) | 16 | 7.7% |
| Southeast (Florida) | 16 | 7.7% |
| South (Texas) | 15 | 7.2% |
| Northeast (Harvard, Boston, Cornell) | 17 | 8.2% |
| Other | 25 | 12.1% |

**Key Observations:**
- ✅ 8 distinct geographic regions
- ✅ Coast-to-coast coverage (California to Mid-Atlantic)
- ✅ No single region dominates (max 22.7%)
- ✅ Balanced East Coast (30.9%) vs. West Coast (19.8%) vs. Central (22.2%)

### Institutional Tier Diversity

**By Law School Ranking:**
- Tier 1 (Top 5: Harvard, Yale, Stanford, Columbia, Chicago): 46 pairs (22.2%)
- Tier 2 (Top 6-15): 41 pairs (19.8%)
- Other (Regional/State schools): 120 pairs (58.0%)

**Key Observations:**
- ✅ Excellent representation of regional law reviews (58%)
- ✅ Not overly dominated by T14 schools
- ✅ Mix of elite and regional perspectives

### Diversity Metrics

**Herfindahl-Hirschman Index (HHI): 582**
- Interpretation: Highly diverse (well below 1500 threshold)
- Comparison:
  - <1500 = High diversity ✅ (we are here)
  - 1500-2500 = Moderate diversity
  - >2500 = Concentrated/monopolistic

**Concentration Ratios:**
- CR3 (top 3): 22.7% ✅ (healthy competition)
- CR5 (top 5): 37.2% ✅
- CR10 (top 10): 67.6% ✅

### Law Review Diversity Verdict

✅ **EXCELLENT - No additional law reviews needed**

**Rationale:**
1. 20 unique journals is sufficient for capturing law review structural diversity
2. HHI of 582 indicates highly balanced distribution
3. Geographic, tier, and size diversity all well-represented
4. Adding more law reviews would yield diminishing returns

**Recommendation:** Focus resources on non-law-review content (see Part 2).

---

## Part 2: Non-Law-Review HTML-PDF Pair Diversity

### Current Status

**Non-law-review PDF-HTML pairs:** 0 (ZERO)

**Breakdown:**
- Science journals: 0
- Medical journals: 0
- Engineering papers: 0
- Government documents: 0
- Policy papers: 0
- Technical reports: 0
- Books/monographs: 0
- Conference proceedings: 0

### Critical Risk Assessment

🔴 **SEVERE OVERFITTING RISK**

Training on 100% law review documents means DoclingBERT v3.1 will learn:

**Law-Specific Patterns (will overfit to):**
1. **Citation styles:** Bluebook citations exclusively
2. **Structural conventions:**
   - Single-column text layout
   - Extensive footnotes (often >30% of content)
   - Section numbering: I, II, III, A, B, C
   - "Part I", "Part II" organizational structure
3. **Vocabulary:** Legal terminology, Latin phrases, case citations
4. **Header/footer patterns:** Law review-specific formatting
5. **Figure/table styles:** Minimal figures, mostly text
6. **Font conventions:** Times New Roman, serif fonts

**Patterns DoclingBERT Will Likely Miss:**

**Science/Engineering Documents:**
- Multi-column layouts (Nature, Science use 2-3 columns)
- Equations and mathematical notation
- Algorithm pseudocode blocks
- Complex figures with sub-panels (Fig 1A, 1B, etc.)
- Different citation styles (APA, Vancouver, IEEE)
- Methods/Results/Discussion structure
- Supplementary materials sections

**Medical Documents:**
- Clinical trial formats (CONSORT diagrams)
- Patient demographics tables
- Statistical analysis sections
- Different header patterns (BMJ, JAMA styles)
- Abbreviations tables
- Ethics statements

**Government Documents:**
- Executive summary sections
- Policy recommendation formats
- Budget tables and fiscal year references
- Agency-specific formatting
- Public domain declarations
- Different page numbering systems

**Impact Prediction:**
- Accuracy on law reviews: 90-95% (good)
- Accuracy on science journals: 50-70% (poor)
- Accuracy on medical papers: 50-70% (poor)
- Accuracy on government docs: 40-60% (very poor)

### Non-Law Diversity Verdict

❌ **CRITICAL FAILURE - Immediate action required**

**Severity:** HIGH
**Timeline:** Should be addressed BEFORE training v3.1

---

## Part 3: Recommendations

### Priority 1: Collect Non-Law-Review HTML-PDF Pairs (CRITICAL)

**Target:** 150-300 pairs minimum (Issue #30 recommends 250-500)
**Timeline:** 1-2 weeks
**Domains required:** 8-10 distinct types

#### Recommended Collection Strategy

**Tier 1 Sources (Open Access - Easy Collection):**

1. **PubMed Central (Medical/Life Sciences)**
   - Target: 30-50 pairs
   - Access: Open, bulk FTP available
   - Format: XML → HTML + PDF
   - Collection time: 2-3 hours
   - Example journals: PLOS, eLife, BMC series

2. **arXiv (Physics/Math/CS/Econ)**
   - Target: 30-50 pairs
   - Access: Open, S3 API
   - Format: LaTeX → HTML + PDF (using ar5iv)
   - Collection time: 2-3 hours
   - Covers: multiple STEM domains

3. **Government Documents (Policy)**
   - Target: 20-30 pairs
   - Sources: GAO.gov, CRS, White House
   - Access: Public domain, direct download
   - Collection time: 2-3 hours

4. **PLOS (Multidisciplinary Science)**
   - Target: 20-30 pairs
   - Access: Open, API available
   - Format: HTML + PDF both provided
   - Collection time: 2-3 hours

5. **eLife (Biomedical/Life Sciences)**
   - Target: 20-30 pairs
   - Access: Open, API
   - Format: Clean HTML + PDF
   - Collection time: 2-3 hours

**Tier 2 Sources (Institutional Access - Medium Difficulty):**

6. **Annual Reviews (Science)**
   - Target: 15-20 pairs
   - Access: Institutional subscription needed
   - Multiple domains: Chemistry, Biology, Ecology

7. **IEEE Xplore (Engineering)**
   - Target: 15-20 pairs
   - Access: Institutional subscription
   - Technical papers with equations/algorithms

**Total Estimated Time:** 15-20 hours of collection work

#### Minimum Viable Diversity

To prevent severe overfitting, collect AT LEAST:
- **30 science papers** (physics, chemistry, biology mix)
- **30 medical papers** (clinical trials, systematic reviews)
- **25 engineering papers** (computer science, electrical engineering)
- **25 government documents** (GAO reports, CRS reports)
- **20 arXiv preprints** (math, CS, econ mix)
- **20 PLOS papers** (open access multidisciplinary)

**Total: 150 pairs** (minimum viable)

This gives ~42% non-law content (150 non-law / 357 total), which should prevent severe overfitting.

### Priority 2: Balance Training Data (After Collection)

**Recommended final corpus composition:**
- Law reviews: 35-45% (207 pairs)
- Science/Engineering: 25-35% (100-150 pairs)
- Medical/Health: 15-25% (75-100 pairs)
- Government/Policy: 10-15% (50-75 pairs)

**Total target:** 400-500 pairs

### Priority 3: Validate Diversity (Before Training)

Before training v3.1, verify:
1. ✅ At least 8 distinct document types
2. ✅ No single domain >40% of corpus
3. ✅ Multi-column layouts represented (>20% of corpus)
4. ✅ Multiple citation styles (Bluebook, APA, Vancouver, IEEE)
5. ✅ Various header/footer conventions
6. ✅ Figures/tables/equations present in sufficient quantity

---

## Part 4: Immediate Next Steps

### Week 1: Rapid Collection (Open Access Sources)

**Day 1-2: PubMed Central**
```bash
# Use PMC bulk FTP to download 30-50 article XML + PDFs
# Convert XML to clean HTML
# Validate HTML-PDF pairing
```

**Day 3-4: arXiv**
```bash
# Use arXiv API to collect recent papers
# Use ar5iv.org for HTML rendering
# Download corresponding PDFs
```

**Day 5: Government Documents**
```bash
# Scrape GAO.gov for reports (HTML + PDF both available)
# Download CRS reports from government sites
```

**Day 6-7: PLOS + eLife**
```bash
# Use PLOS API for article discovery
# Download HTML + PDF pairs
# Validate quality
```

**Expected Result:** 150-180 non-law pairs collected

### Week 2: Validation & Integration

**Day 8-9: Quality Check**
- Verify HTML-PDF text matching (>70% similarity)
- Check structural elements (headings, figures, captions)
- Remove low-quality pairs

**Day 10-11: Corpus Integration**
- Merge with existing law review corpus
- Generate diversity metrics
- Validate class balance

**Day 12-14: Test Extraction**
- Run Docling on sample of non-law PDFs
- Verify label extraction quality
- Adjust patterns if needed

### Week 3: Ready for Training

- Final corpus: 350-400 pairs
- Law reviews: ~40%
- Non-law: ~60%
- Ready to train v3.1

---

## Part 5: Automated Collection Scripts

### Collection Priority Order

1. **PubMed Central** (easiest, best quality)
   - Script: `scripts/data_collection/collect_pubmed_central.py`
   - Status: Need to create

2. **arXiv** (easy, good diversity)
   - Script: `scripts/data_collection/collect_arxiv_papers.py`
   - Status: Need to create

3. **PLOS** (easy, clean format)
   - Script: `scripts/data_collection/collect_plos_papers.py`
   - Status: Need to create

4. **GAO Documents** (easy, public domain)
   - Script: `scripts/data_collection/collect_gao_reports.py`
   - Status: Need to create

### Collection Script Template

```python
#!/usr/bin/env python3
"""
Collect HTML-PDF pairs from [SOURCE]

Target: 30-50 pairs
Domain: [medical/science/engineering/government]
"""

import requests
from pathlib import Path
import time

def discover_articles(limit=50):
    """Discover articles from API or web scraping."""
    pass

def download_pair(article_id, output_dir):
    """Download both HTML and PDF for article."""
    pass

def validate_pair(html_path, pdf_path):
    """Verify HTML-PDF pairing quality."""
    pass

def main():
    output_dir = Path("data/raw_html_pdf_pairs/[source]")
    output_dir.mkdir(parents=True, exist_ok=True)

    articles = discover_articles(limit=50)

    for article in articles:
        download_pair(article['id'], output_dir)
        # Rate limiting
        time.sleep(2)

if __name__ == "__main__":
    main()
```

---

## Summary

**Law Review Diversity:** ✅ EXCELLENT (no action needed)
- 20 journals, highly balanced (HHI=582)
- 8 geographic regions
- Mix of elite and regional schools
- **Recommendation:** STOP collecting law reviews

**Non-Law Diversity:** ❌ CRITICAL FAILURE (immediate action required)
- 0 non-law pairs
- 100% legal document formatting
- Severe overfitting risk
- **Recommendation:** Collect 150-300 non-law pairs BEFORE training v3.1

**Priority Actions:**
1. **Week 1:** Collect 150-180 open-access pairs (PubMed, arXiv, PLOS, GAO)
2. **Week 2:** Validate and integrate
3. **Week 3:** Train v3.1 with diverse corpus

**Risk if we proceed without non-law diversity:**
- Model will fail on 50%+ of real-world documents
- Limited to legal document processing only
- Not generalizable to science, medicine, engineering, policy domains

---

**Last updated:** October 17, 2025
**Next review:** After collecting first 50 non-law pairs
