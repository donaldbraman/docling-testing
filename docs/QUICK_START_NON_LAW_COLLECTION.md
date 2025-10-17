# Quick Start: Non-Law-Review Collection

**Goal:** Collect 150+ HTML-PDF pairs from diverse non-law sources
**Status:** ✅ Scripts ready to deploy
**Timeline:** Start now, complete in 1-2 weeks

---

## 📦 What's Ready

### ✅ High-Priority (Ready to Deploy NOW)

**Agent 1: PubMed Central**
- 📄 Instructions: `docs/agents/AGENT_1_PUBMED_CENTRAL.md`
- 🐍 Script: `scripts/data_collection/collect_pubmed_central.py`
- 🎯 Target: 40 medical/biomedical pairs
- ⏱️ Time: 5-10 minutes runtime
- ✅ Status: **READY TO RUN**

**Agent 2: arXiv**
- 📄 Instructions: `docs/agents/AGENT_2_ARXIV.md`
- 🐍 Script: `scripts/data_collection/collect_arxiv_papers.py`
- 🎯 Target: 40 STEM preprint pairs
- ⏱️ Time: 10-15 minutes runtime
- ✅ Status: **READY TO RUN**

### ⏳ Medium-Priority (Need Scripts)

**Agent 3: PLOS** - Target: 30 pairs (open-access science)
**Agent 4: GAO Reports** - Target: 20 pairs (government documents)
**Agent 5: eLife** - Target: 20 pairs (biomedical)

---

## 🚀 Deploy in 3 Steps

### Step 1: Test PubMed Central Collection (5 min)

```bash
cd /Users/donaldbraman/Documents/GitHub/docling-testing

# Test with 5 pairs first
uv run python scripts/data_collection/collect_pubmed_central.py --target 5

# Check results
ls data/raw_html/pmc_*.html | wc -l
ls data/raw_pdf/pmc_*.pdf | wc -l
```

**Expected Output:**
- 5 HTML files in `data/raw_html/`
- 5 PDF files in `data/raw_pdf/`
- Report in `data/collection_logs/pubmed_central/COLLECTION_REPORT.md`

### Step 2: Run Full PubMed Central Collection (10 min)

```bash
# Collect 40-50 pairs
uv run python scripts/data_collection/collect_pubmed_central.py --target 50
```

**What it does:**
1. Searches PMC API for recent open-access articles (2024)
2. Downloads HTML and PDF for each article
3. Validates file quality (size checks, format verification)
4. Generates detailed collection report
5. Creates JSON manifest of collected articles

**Success Criteria:**
- ✓ 40+ complete pairs collected
- ✓ Diverse medical topics (5+ journals)
- ✓ No blocking/rate limit issues
- ✓ Report generated with statistics

### Step 3: Run arXiv Collection (15 min)

```bash
# Collect 40-50 pairs across multiple STEM categories
uv run python scripts/data_collection/collect_arxiv_papers.py --target 50 --per-category 10
```

**What it does:**
1. Queries arXiv API across 6 categories (CS, physics, math, econ)
2. Downloads PDFs from arxiv.org
3. Downloads HTML from ar5iv.org (LaTeX rendering)
4. Validates both files
5. Generates report with category distribution

**Success Criteria:**
- ✓ 40+ complete pairs collected
- ✓ At least 4 different STEM categories
- ✓ Equations and math notation visible in HTML
- ✓ Report shows category diversity

---

## 📊 Expected Results (After Steps 1-3)

**Immediate Progress:**
- **~80-100 non-law pairs** collected (PMC: 40-50, arXiv: 40-50)
- **2 distinct domains** (medical + STEM)
- **~30 minutes** total runtime
- **20-30% corpus diversity** achieved (80-100 non-law / 287-307 total)

**Files Created:**
```
data/
├── raw_html/
│   ├── pmc_*.html (40-50 files)
│   └── arxiv_*.html (40-50 files)
├── raw_pdf/
│   ├── pmc_*.pdf (40-50 files)
│   └── arxiv_*.pdf (40-50 files)
└── collection_logs/
    ├── pubmed_central/
    │   ├── COLLECTION_REPORT.md
    │   └── collected_articles.json
    └── arxiv/
        ├── COLLECTION_REPORT.md
        └── collected_papers.json
```

---

## ⏭️ Next Steps (Optional - For Full 150+ Target)

### Create Remaining Scripts (2-3 hours)

Following the PMC/arXiv pattern, create:

**PLOS Collection** (30 pairs, easy):
```python
# Similar to PMC but uses PLOS Search API
# API: https://api.plos.org/search
# Pattern: journals.plos.org/{journal}/article?id={doi}
```

**GAO Reports** (20 pairs, moderate):
```python
# Web scraping (no API)
# Browse: https://www.gao.gov/reports-testimonies
# Public domain, direct HTML/PDF downloads
```

**eLife Collection** (20 pairs, easy):
```python
# Similar to PLOS
# API: https://api.elifesciences.org/search
# Pattern: elifesciences.org/articles/{id}
```

### Deploy All 5 Agents (1 week)

Once all scripts ready:
```bash
# Run all 5 in sequence (or deploy as parallel agents)
uv run python scripts/data_collection/collect_pubmed_central.py --target 50
uv run python scripts/data_collection/collect_arxiv_papers.py --target 50
uv run python scripts/data_collection/collect_plos_papers.py --target 30
uv run python scripts/data_collection/collect_gao_reports.py --target 20
uv run python scripts/data_collection/collect_elife_papers.py --target 20
```

**Final Result:** 150-180 non-law pairs

---

## 🎯 Success Metrics

### Minimum Viable Diversity (80-100 pairs)
- ✅ Medical domain (PMC): 40-50 pairs
- ✅ STEM domain (arXiv): 40-50 pairs
- ✅ 2 distinct document types
- ✅ Multi-column layouts (medical journals)
- ✅ Equations/algorithms (arXiv)
- ✅ Different citation styles (Vancouver, arXiv style)

**Status:** ACHIEVABLE TODAY (30 min runtime)

### Full Diversity Target (150-180 pairs)
- Medical/biomedical: 60-80 pairs (PMC + eLife)
- STEM preprints: 40-50 pairs (arXiv)
- Open-access science: 30-40 pairs (PLOS)
- Government documents: 20 pairs (GAO)
- 5 distinct source types

**Status:** Achievable in 1-2 weeks (need remaining scripts)

---

## 🔍 Quality Validation

After collection, validate pairs:

```bash
# Check file counts
echo "HTML files: $(ls data/raw_html/{pmc,arxiv}_*.html 2>/dev/null | wc -l)"
echo "PDF files: $(ls data/raw_pdf/{pmc,arxiv}_*.pdf 2>/dev/null | wc -l)"

# Review collection reports
cat data/collection_logs/pubmed_central/COLLECTION_REPORT.md
cat data/collection_logs/arxiv/COLLECTION_REPORT.md
```

**Quality Checks:**
- [ ] HTML files >10KB each (full text, not abstracts)
- [ ] PDF files >100KB each (complete documents)
- [ ] Success rate >90% per source
- [ ] No blocking/rate limit incidents
- [ ] Reports show topic/category diversity

---

## 📈 Integration with Existing Corpus

**Current State:**
- Law reviews: 207 pairs (100%)
- Non-law: 0 pairs (0%)

**After PMC + arXiv (Today):**
- Law reviews: 207 pairs (68-72%)
- Non-law: 80-100 pairs (28-32%)
- **Total:** 287-307 pairs

**After Full Collection (1-2 weeks):**
- Law reviews: 207 pairs (58%)
- Non-law: 150 pairs (42%)
- **Total:** 357 pairs

**Diversity Achievement:**
- ✅ No single domain >70%
- ✅ Multiple document types (legal, medical, STEM, science, government)
- ✅ Multiple citation styles
- ✅ Multi-column and single-column layouts
- ✅ Equations, figures, tables represented

---

## ⚠️ Troubleshooting

### PMC Collection Issues

**Problem:** 403 Forbidden errors
**Solution:** Check user-agent, increase delay to 1s

**Problem:** Missing PDFs
**Solution:** Normal - some articles don't have PDFs, script will skip

### arXiv Collection Issues

**Problem:** ar5iv HTML rendering fails
**Solution:** Script tries alternative arXiv native HTML automatically

**Problem:** 429 Rate Limit
**Solution:** Delay is already 3s (arXiv requirement), wait and retry

---

## 🎉 Quick Win: Start Now!

**Recommended approach:**
1. ✅ Run PMC collection now (5-10 min)
2. ✅ Run arXiv collection now (10-15 min)
3. ✅ Review reports and validate quality
4. ✅ You'll have 80-100 non-law pairs in 30 minutes!
5. ⏳ Create remaining scripts later (optional, for full 150 target)

**Commands:**
```bash
# Start immediately
cd /Users/donaldbraman/Documents/GitHub/docling-testing

# PMC collection (medical diversity)
uv run python scripts/data_collection/collect_pubmed_central.py --target 50

# arXiv collection (STEM diversity)
uv run python scripts/data_collection/collect_arxiv_papers.py --target 50

# Check results
ls data/raw_html/{pmc,arxiv}_*.html | wc -l
ls data/raw_pdf/{pmc,arxiv}_*.pdf | wc -l
```

That's it! You'll have significant corpus diversity in under an hour.

---

**Last Updated:** October 17, 2025
**Status:** ✅ Ready to deploy
**Next Action:** Run PMC + arXiv scripts now!
