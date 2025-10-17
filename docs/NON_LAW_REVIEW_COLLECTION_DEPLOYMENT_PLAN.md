# Non-Law-Review Collection Deployment Plan
**Based on Successful Law Review Collection Pattern**

**Date:** October 17, 2025
**Goal:** Collect 150-180 HTML-PDF pairs from 5 diverse sources
**Timeline:** 5-7 days (parallel agents)
**Pattern:** Proven law review agent deployment strategy

---

## 📋 Executive Summary

We're adapting the **successful law review collection pattern** for non-law-review sources. The law review approach worked because:

1. ✅ **Detailed reconnaissance instructions** (robots.txt, site structure, URL patterns)
2. ✅ **Multi-stage discovery pipeline** (Browse Recent, Search+Crawl, RSS Feeds)
3. ✅ **Clear tool selection guidance** (WebFetch vs Bash vs Python)
4. ✅ **Ethical crawling** (rate limiting, compliance)
5. ✅ **Success criteria** (10+ pairs minimum, full articles)
6. ✅ **Automated scripts** (Python scripts per source)
7. ✅ **Comprehensive reporting** (detailed collection summaries)

We'll deploy **5 parallel agents**, each with source-specific instructions following this proven pattern.

---

## 🎯 Agent Assignments & Instructions

### Agent 1: PubMed Central (PMC) Collection

**Target:** 40 medical/biomedical article pairs
**Source:** https://www.ncbi.nlm.nih.gov/pmc/
**Estimated Time:** 1-2 days

**Instructions File:** `docs/agents/AGENT_1_PUBMED_CENTRAL.md`

**Key Strategies:**
- Use PMC E-utilities API for article discovery
- Focus on recent open-access articles (2024-2025)
- Categories: Clinical trials, systematic reviews, molecular biology
- Download JATS XML → HTML + PDF
- Rate limit: 3 requests/second (0.4s delay)

**Success Criteria:**
- 40+ complete HTML-PDF pairs
- Diverse medical subfields (oncology, cardiology, neurology, etc.)
- Multi-column layouts represented
- Vancouver citation style
- Complex figures with sub-panels

---

### Agent 2: arXiv Collection

**Target:** 40 STEM preprint pairs
**Source:** https://arxiv.org + https://ar5iv.org
**Estimated Time:** 1-2 days

**Instructions File:** `docs/agents/AGENT_2_ARXIV.md`

**Key Strategies:**
- Use arXiv API for article discovery
- Categories: cs.AI, cs.LG, physics.comp-ph, econ.GN, math.ST
- Download PDFs from arxiv.org
- Get HTML from ar5iv.org (LaTeX → HTML rendering)
- Rate limit: 1 request/3 seconds

**Success Criteria:**
- 40+ complete HTML-PDF pairs
- Heavy equations and mathematical notation
- Algorithm pseudocode blocks
- Multi-domain coverage (CS, physics, econ, math)
- LaTeX rendering quality verified

---

### Agent 3: PLOS Collection

**Target:** 30 open-access multidisciplinary pairs
**Source:** https://journals.plos.org
**Estimated Time:** 1 day

**Instructions File:** `docs/agents/AGENT_3_PLOS.md`

**Key Strategies:**
- Use PLOS Search API for article discovery
- Focus on research articles (not corrections/editorials)
- Journals: PLOS ONE, Biology, Medicine, Computational Biology
- Download HTML + PDF from article pages
- Rate limit: 2-3 seconds between requests

**Success Criteria:**
- 30+ complete HTML-PDF pairs
- Diverse biological/medical topics
- Figures with DOIs
- Supporting information sections
- Data availability statements

---

### Agent 4: GAO Reports Collection

**Target:** 20 government report pairs
**Source:** https://www.gao.gov
**Estimated Time:** 1 day

**Instructions File:** `docs/agents/AGENT_4_GAO_REPORTS.md`

**Key Strategies:**
- Browse GAO reports page (no API)
- Filter: Reports (not testimonies), recent (2024-2025)
- Download HTML (report page) + PDF
- Focus on full reports (>50 pages)
- Rate limit: 2.5 seconds between requests

**Success Criteria:**
- 20+ complete HTML-PDF pairs
- Diverse policy topics (healthcare, defense, economy, environment)
- Government document formatting patterns
- Executive summaries
- Budget tables and fiscal data

---

### Agent 5: eLife Collection

**Target:** 20 high-quality biomedical pairs
**Source:** https://elifesciences.org
**Estimated Time:** 1 day

**Instructions File:** `docs/agents/AGENT_5_ELIFE.md`

**Key Strategies:**
- Use eLife API for article discovery
- Categories: Neuroscience, genetics, cell biology, immunology
- Download article HTML + PDF
- Rate limit: 2-3 seconds between requests

**Success Criteria:**
- 20+ complete HTML-PDF pairs
- High-quality HTML rendering
- Rich figures and interactive elements
- Editorial structure
- Decision letters (if available)

---

## 📂 File Structure

```
docs/
├── guides/
│   ├── LAW_REVIEW_COLLECTION_STRATEGIES.md (existing ✓)
│   └── NON_LAW_REVIEW_COLLECTION_STRATEGY.md (created ✓)
│
└── agents/
    ├── AGENT_1_PUBMED_CENTRAL.md (to create)
    ├── AGENT_2_ARXIV.md (to create)
    ├── AGENT_3_PLOS.md (to create)
    ├── AGENT_4_GAO_REPORTS.md (to create)
    └── AGENT_5_ELIFE.md (to create)

scripts/
└── data_collection/
    ├── collect_pubmed_central.py (to create)
    ├── collect_arxiv_papers.py (to create)
    ├── collect_plos_papers.py (to create)
    ├── collect_gao_reports.py (to create)
    └── collect_elife_papers.py (to create)

data/
└── collection_logs/
    ├── pubmed_central/
    │   ├── progress.txt
    │   ├── COLLECTION_REPORT.md
    │   └── collected_articles.json
    ├── arxiv/
    ├── plos/
    ├── gao_reports/
    └── elife/
```

---

## 🛠️ Implementation Steps

### Step 1: Create Agent Instructions (1 hour)

For each agent, create detailed instructions following the law review pattern:

**Template Structure:**
```markdown
# Agent [N]: [SOURCE NAME] Collection Instructions

## Objective
Collect [TARGET] HTML-PDF pairs from [SOURCE]

## Stage 1: Reconnaissance
- Check API documentation / robots.txt
- Understand site structure and URL patterns
- Test simple API query
- Document findings

## Stage 2: Discovery Strategy
- [Method 1]: Browse recent articles
- [Method 2]: API-based search
- [Method 3]: Archive browsing
- Select best method based on reconnaissance

## Stage 3: Collection
- Use provided Python script or curl/WebFetch
- Download HTML and PDF for each article
- Validate file quality
- Rate limiting: [X] seconds between requests

## Stage 4: Reporting
- Create COLLECTION_REPORT.md
- Document collected articles
- Report success rate and issues

## Success Criteria
- [TARGET]+ complete pairs
- [QUALITY CRITERIA]
- No blocking incidents
- Comprehensive documentation
```

**Files to Create:**
1. `docs/agents/AGENT_1_PUBMED_CENTRAL.md`
2. `docs/agents/AGENT_2_ARXIV.md`
3. `docs/agents/AGENT_3_PLOS.md`
4. `docs/agents/AGENT_4_GAO_REPORTS.md`
5. `docs/agents/AGENT_5_ELIFE.md`

---

### Step 2: Create Collection Scripts (2-3 hours)

For each source, create a Python collection script following the template:

**Common Features:**
- API/web scraping for article discovery
- HTML and PDF download with error handling
- Rate limiting (respect each source's limits)
- Progress tracking and logging
- Validation (file sizes, completeness)
- Report generation

**Scripts to Create:**
1. `scripts/data_collection/collect_pubmed_central.py`
   - Use requests + lxml for PMC API
   - JATS XML parsing
   - 0.4s delay between requests

2. `scripts/data_collection/collect_arxiv_papers.py`
   - arXiv API for discovery
   - ar5iv.org for HTML
   - 3s delay between requests

3. `scripts/data_collection/collect_plos_papers.py`
   - PLOS Search API
   - Direct HTML/PDF downloads
   - 2.5s delay between requests

4. `scripts/data_collection/collect_gao_reports.py`
   - Web scraping (no API)
   - BeautifulSoup for parsing
   - 2.5s delay between requests

5. `scripts/data_collection/collect_elife_papers.py`
   - eLife API
   - Direct HTML/PDF downloads
   - 2.5s delay between requests

---

### Step 3: Deploy Agents (5-7 days, parallel)

**Day 1-2: Deploy Agents 1-5 in Parallel**
```bash
# Agent 1: PMC (1-2 days)
claude --agent "Agent 1: Collect 40 PubMed Central pairs. Instructions: docs/agents/AGENT_1_PUBMED_CENTRAL.md"

# Agent 2: arXiv (1-2 days)
claude --agent "Agent 2: Collect 40 arXiv pairs. Instructions: docs/agents/AGENT_2_ARXIV.md"

# Agent 3: PLOS (1 day)
claude --agent "Agent 3: Collect 30 PLOS pairs. Instructions: docs/agents/AGENT_3_PLOS.md"

# Agent 4: GAO (1 day)
claude --agent "Agent 4: Collect 20 GAO report pairs. Instructions: docs/agents/AGENT_4_GAO_REPORTS.md"

# Agent 5: eLife (1 day)
claude --agent "Agent 5: Collect 20 eLife pairs. Instructions: docs/agents/AGENT_5_ELIFE.md"
```

**Day 3-5: Monitor Progress**
- Check collection logs daily
- Address any blocking issues
- Adjust strategies if needed

**Day 6-7: Validation**
- Review collected pairs
- Verify HTML-PDF alignment
- Remove low-quality pairs

---

### Step 4: Validation & Integration (2-3 days)

**Validation Criteria:**
```python
def validate_html_pdf_pair(html_path, pdf_path):
    """
    Validate HTML-PDF pairing quality.

    Checks:
    - Both files exist
    - Minimum file sizes (HTML >10KB, PDF >100KB)
    - Text similarity >70%
    - Figure numbering consistency
    - Structural elements present
    """
    pass
```

**Integration Steps:**
1. Run validation script on all collected pairs
2. Remove failed pairs
3. Merge with existing law review corpus
4. Generate final diversity metrics
5. Create corpus manifest

---

## 📊 Expected Outcomes

### Collection Targets

| Source | Target | Stretch | Domain |
|--------|--------|---------|--------|
| PubMed Central | 40 | 50 | Medical/Biomedical |
| arXiv | 40 | 50 | STEM (CS, Physics, Math, Econ) |
| PLOS | 30 | 40 | Multidisciplinary Science |
| GAO Reports | 20 | 25 | Government/Policy |
| eLife | 20 | 25 | High-Quality Biomedical |
| **Total** | **150** | **190** | **5 domains** |

### Final Corpus Composition

**After integration with existing law reviews:**
- **Law reviews:** ~207 pairs (40%)
- **Medical/biomedical:** ~60 pairs (12%)
- **STEM preprints:** ~40 pairs (8%)
- **Multidisciplinary science:** ~30 pairs (6%)
- **Government reports:** ~20 pairs (4%)
- **Total:** ~357-407 pairs

**Diversity Achieved:**
- ✅ 6+ distinct document types
- ✅ No single domain >40% of corpus
- ✅ Multi-column layouts represented
- ✅ Multiple citation styles (Bluebook, Vancouver, APA, IEEE)
- ✅ Various header/footer conventions
- ✅ Figures/tables/equations present

---

## ⚠️ Risk Mitigation

### Potential Risks

1. **API Rate Limiting**
   - **Mitigation:** Respect documented limits, add generous delays
   - **Backup:** Manual collection if automated blocked

2. **HTML Quality Issues (especially arXiv)**
   - **Mitigation:** Use ar5iv.org for LaTeX rendering
   - **Validation:** Check equation rendering quality
   - **Backup:** Use native arXiv HTML if available

3. **Agent Blocking**
   - **Mitigation:** Polite user agents, rate limiting, robots.txt compliance
   - **Backup:** Pause and retry later, or manual collection

4. **Time Overruns**
   - **Mitigation:** Start with easiest sources (PLOS, GAO)
   - **Backup:** Can accept 100-120 pairs if needed (still 30% non-law)

5. **HTML-PDF Misalignment**
   - **Mitigation:** Strict validation criteria (>70% similarity)
   - **Backup:** Remove low-quality pairs

---

## 🎯 Success Metrics

### Quantitative Targets
- ✅ 150+ non-law HTML-PDF pairs
- ✅ 5+ distinct source types
- ✅ 95%+ success rate per agent
- ✅ 0 blocking incidents
- ✅ >70% HTML-PDF text similarity

### Qualitative Targets
- ✅ Multi-column layouts present
- ✅ Equations/algorithms present (arXiv)
- ✅ Clinical trial formats (PMC)
- ✅ Government document patterns (GAO)
- ✅ Different citation styles

### Timeline Targets
- ✅ Week 1: Collection complete (150-180 pairs)
- ✅ Week 2: Validation and integration
- ✅ Week 3: Ready for v3.1 training

---

## 📝 Deliverables

### Per Agent
1. **Collection Script** (`scripts/data_collection/collect_[source].py`)
2. **Collection Report** (`data/collection_logs/[source]/COLLECTION_REPORT.md`)
3. **Article Manifest** (`data/collection_logs/[source]/collected_articles.json`)
4. **Progress Log** (`data/collection_logs/[source]/progress.txt`)
5. **HTML Files** (`data/raw_html/[source]_*.html`)
6. **PDF Files** (`data/raw_pdf/[source]_*.pdf`)

### Overall
1. **Consolidated Report** (`docs/NON_LAW_REVIEW_COLLECTION_SUMMARY.md`)
2. **Corpus Diversity Analysis** (`docs/FINAL_CORPUS_DIVERSITY_REPORT.md`)
3. **Validated Corpus Manifest** (`data/corpus_manifest.json`)
4. **Training-Ready Dataset** (`data/diverse_corpus.csv`)

---

## 🚀 Ready to Deploy?

**Estimated Total Time:**
- **Preparation:** 3-4 hours (agent instructions + scripts)
- **Collection:** 5-7 days (parallel agents)
- **Validation:** 2-3 days
- **Total:** ~2 weeks start to finish

**Resources Needed:**
- 5 parallel agent sessions
- Python environment (via uv)
- Internet access for APIs
- ~2-3 GB storage for files

**Next Step:** Create the 5 agent instruction files and 5 collection scripts, then deploy!

---

**Status:** READY FOR APPROVAL ✓
**Confidence:** HIGH (based on proven law review pattern)
**Risk:** LOW (open-access sources, ethical crawling)
