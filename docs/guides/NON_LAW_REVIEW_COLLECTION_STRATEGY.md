# Non-Law-Review HTML-PDF Pair Collection Strategy
## Multi-Agent Parallel Collection Guide for Diverse Academic Sources

**Objective:** Each agent collects 30-50 HTML-PDF pairs from assigned scientific/medical/government sources
**Target:** Maximum diversity across document types, layouts, and citation styles
**Context:** Preventing DoclingBERT v3.1 overfitting to law review patterns only

---

## 🎯 Success Criteria

Per Agent/Source:
- ✅ Collect **minimum 30 complete HTML-PDF pairs** (stretch goal: 50+)
- ✅ All pairs are **full articles/reports** (not abstracts, summaries, or short notes)
- ✅ Files are **complete and readable**
- ✅ Both HTML and PDF exist for each article
- ✅ **Diverse structural patterns** (multi-column, equations, figures, tables)
- ✅ **No blocking/blacklisting** occurred
- ✅ **Documentation** of strategies tried and success rates

---

## 🛠️ Agent Setup & Tools

**Agent Type:** `general-purpose` (has access to all tools)

### ✅ Tools & Dependencies Status

All required tools are installed and ready:

```
System Tools:
✓ curl          /usr/bin/curl        (HTTP requests, file downloads)
✓ wget          /opt/homebrew/bin/wget (Alternative downloads)

Python Packages (via uv):
✓ requests      2.31.0+  (HTTP with sessions, automatic retries)
✓ beautifulsoup4 4.12.0+ (HTML parsing, CSS selectors)
✓ lxml          5.4.0+   (XML/HTML processing - critical for PubMed)
✓ pandas        2.1.0+   (Data handling, CSV output)
✓ pypdf         6.1.1+   (PDF validation)

Built-in Tools:
✓ WebFetch      (HTML retrieval with JavaScript rendering)
✓ Bash          (Shell commands, curl, wget)
✓ Python        (Script execution)
✓ File Ops      (Read, Write, Glob, Grep)
```

### Tool Selection by Source Type

| Source | Primary Tool | Backup Tool | Best For |
|--------|--|--|--|
| PubMed Central | Python (requests) | Bash (curl) | XML/API parsing |
| arXiv | Bash (curl) | Python (requests) | Bulk downloads, LaTeX |
| PLOS | Python (requests) | WebFetch | API-based discovery |
| GAO.gov | WebFetch | Bash (curl) | HTML browsing |
| eLife | Python (requests) | WebFetch | API + HTML rendering |

---

## 📚 Source Priority & Target Distribution

### Tier 1: Open Access - Easy Collection (Target: 150 pairs total)

#### 1. PubMed Central (Medical/Life Sciences)
**Target:** 40 pairs
**Access:** Open, bulk FTP + API
**API:** E-utilities (https://www.ncbi.nlm.nih.gov/books/NBK25501/)
**Rate Limit:** 3 requests/second without API key, 10 req/s with key

**Why PMC:**
- Excellent HTML-PDF pairing (both provided)
- Diverse medical topics (clinical trials, reviews, basic research)
- Multi-column layouts common
- Different citation style (Vancouver)
- Complex figures with sub-panels
- Statistical tables
- Methods/Results/Discussion structure

**Collection Approach:**
- Use PMC API to search recent open-access articles
- Filter for: full-text available, PDF available, >5000 words
- Download XML (convert to HTML) + PDF
- Focus on: PLOS journals, BMC series, eLife, Nature Communications (OA)

#### 2. arXiv (Physics/Math/CS/Economics)
**Target:** 40 pairs
**Access:** Open, S3 API + ar5iv HTML rendering
**API:** arXiv API (https://info.arxiv.org/help/api/index.html)
**Rate Limit:** 1 request/3 seconds

**Why arXiv:**
- LaTeX source → HTML (via ar5iv.org)
- Heavy equations and mathematical notation
- Algorithm pseudocode
- Different structural patterns
- Multi-domain coverage (physics, CS, econ, math)
- Pre-print format (less polished than journals)

**Collection Approach:**
- Query arXiv API for recent papers (last 6 months)
- Categories: cs.AI, cs.LG, physics.comp-ph, econ.GN, math.ST
- Download PDFs from arxiv.org
- Get HTML from ar5iv.org (LaTeX → HTML conversion)
- Verify rendering quality

#### 3. PLOS (Open Access Multidisciplinary)
**Target:** 30 pairs
**Access:** Open, REST API
**API:** PLOS Search API (https://api.plos.org/)
**Rate Limit:** Reasonable (no hard limit documented)

**Why PLOS:**
- Clean, standardized HTML + PDF
- Multiple journals (PLOS ONE, Biology, Medicine, Computational Biology)
- Excellent metadata
- Figures with DOIs
- Supporting information sections
- Data availability statements

**Collection Approach:**
- Use PLOS Search API
- Query recent articles (2024-2025)
- Filter: research articles (not corrections/editorials)
- Download both HTML and PDF from article pages
- Verify figure rendering in both formats

#### 4. Government Documents (GAO Reports)
**Target:** 20 pairs
**Access:** Public domain, direct download
**URL:** https://www.gao.gov/reports-testimonies
**Rate Limit:** Self-imposed 2-3 seconds

**Why GAO:**
- Government document formatting (very different from academic)
- Policy recommendations structure
- Budget tables and fiscal data
- Executive summaries
- Different header/footer patterns
- Public domain (no copyright concerns)

**Collection Approach:**
- Browse GAO reports page (browse by topic or date)
- Filter for: Reports (not testimonies), recent (2024-2025)
- Download both HTML ("View Report" page) and PDF
- Focus on: full reports (>50 pages), diverse topics

#### 5. eLife (Biomedical/Life Sciences)
**Target:** 20 pairs
**Access:** Open, API available
**API:** eLife API (https://api.elifesciences.org/documentation)
**Rate Limit:** Reasonable

**Why eLife:**
- High-quality open access journal
- Excellent HTML rendering
- Rich figures and interactive elements
- Editorial structure
- Impact statement sections
- Decision letter and author response

**Collection Approach:**
- Use eLife API to discover recent articles
- Categories: Neuroscience, Genetics, Cell Biology, Immunology
- Download article HTML and PDF
- Verify figure quality in both formats

---

## 🔄 Multi-Stage Discovery Pipeline (Adapted for Non-Law Sources)

### Stage 1: Reconnaissance (5-10 min per source)

**Phase 1A: API Documentation Review**
```
1. Find API documentation
   - PubMed: E-utilities guide
   - arXiv: API documentation
   - PLOS: Search API docs
   - eLife: API documentation
   - GAO: Check for sitemap/RSS (no API)

2. Understand access patterns
   - Authentication required? (Usually no for open access)
   - Rate limits (respect them strictly)
   - Query parameters (search, filter, pagination)
   - Response formats (JSON, XML, RSS)

3. Test API with simple query
   - curl or Python requests
   - Verify response structure
   - Extract article IDs/DOIs
```

**Phase 1B: File Format Analysis**
```
1. HTML structure
   - PubMed: JATS XML → HTML (may need conversion)
   - arXiv: LaTeX → HTML via ar5iv
   - PLOS: Native HTML (clean)
   - GAO: Government HTML (simpler structure)
   - eLife: Rich HTML with embedded media

2. PDF availability patterns
   - Direct download links
   - ViewContent CGI scripts
   - PDF generators
   - Repository URLs

3. Pairing verification
   - Do article IDs match?
   - Content alignment check
   - Figure numbering consistency
```

---

### Stage 2: Source-Specific Collection Strategies

#### Strategy A: PubMed Central Collection

**Reconnaissance:**
```python
# Test PMC API
import requests
base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

# Search for recent open-access articles
search_url = f"{base_url}esearch.fcgi"
params = {
    "db": "pmc",
    "term": "hasabstract AND ffrft[filter]",  # full free text
    "retmax": 50,
    "retmode": "json"
}
response = requests.get(search_url, params=params)
```

**Discovery Method:**
1. Use esearch to find PMC IDs
2. Use efetch to get article metadata (including PDF URL)
3. Download XML (JATS format)
4. Convert XML to HTML or download HTML version
5. Download PDF

**URL Patterns:**
- HTML: `https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{ID}/`
- PDF: `https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{ID}/pdf/`

**Rate Limiting:**
- 3 requests/second (without API key)
- Add 0.4 second delay between requests
- Use polite user agent

**Quality Checks:**
- Verify XML/HTML has full text (not just abstract)
- Verify PDF is complete (>5 pages)
- Check for figures and tables

#### Strategy B: arXiv Collection

**Reconnaissance:**
```python
# Test arXiv API
import requests
base_url = "http://export.arxiv.org/api/query"

params = {
    "search_query": "cat:cs.AI AND submittedDate:[202401* TO 202412*]",
    "start": 0,
    "max_results": 50
}
response = requests.get(base_url, params=params)
```

**Discovery Method:**
1. Use arXiv API to search categories (cs.AI, physics, econ, math)
2. Extract arXiv IDs from API response
3. Download PDFs from `arxiv.org/pdf/{arxiv_id}.pdf`
4. Get HTML from `ar5iv.org/html/{arxiv_id}` (LaTeX → HTML)
5. Verify HTML rendering quality

**URL Patterns:**
- PDF: `https://arxiv.org/pdf/{arxiv_id}.pdf`
- HTML: `https://ar5iv.org/html/{arxiv_id}` (third-party LaTeX renderer)
- Alternative HTML: `https://arxiv.org/html/{arxiv_id}` (newer arXiv HTML)

**Rate Limiting:**
- 1 request per 3 seconds
- Respect arXiv rate limits strictly
- Bulk downloads should use S3 (but not needed for 40 papers)

**Quality Checks:**
- Verify HTML rendered properly (check for equations)
- PDF should have figures
- Check page count (>5 pages)

#### Strategy C: PLOS Collection

**Reconnaissance:**
```python
# Test PLOS API
import requests
base_url = "https://api.plos.org/search"

params = {
    "q": "article_type:Research Article AND publication_date:[2024-01-01T00:00:00Z TO 2025-12-31T23:59:59Z]",
    "rows": 50,
    "fl": "id,title,author,publication_date,journal"
}
response = requests.get(base_url, params=params)
```

**Discovery Method:**
1. Use PLOS Search API to find recent research articles
2. Extract DOIs from search results
3. Construct article URLs: `journals.plos.org/plosone/article?id={doi}`
4. Download HTML from article page
5. Download PDF from article page (direct link or via CrossRef)

**URL Patterns:**
- HTML: `https://journals.plos.org/{journal}/article?id=10.1371/journal.{journal}.{id}`
- PDF: `https://journals.plos.org/{journal}/article/file?id={doi}&type=printable`

**Rate Limiting:**
- 2-3 seconds between requests
- Be respectful (no hard limit but don't abuse)

**Quality Checks:**
- Verify HTML has full text
- PDF should have figures and proper formatting
- Check for supporting information availability

#### Strategy D: GAO Reports Collection

**Reconnaissance:**
```bash
# Check GAO site structure
curl -s https://www.gao.gov/reports-testimonies | grep -o 'href="/products/[^"]*"' | head -20
```

**Discovery Method:**
1. Browse https://www.gao.gov/reports-testimonies
2. Filter by: Reports (not testimonies), Recent date range
3. For each report:
   - Extract report ID (e.g., GAO-24-12345)
   - Get HTML: `gao.gov/products/{report_id}`
   - Get PDF: `gao.gov/assets/{report_id}.pdf`

**URL Patterns:**
- HTML: `https://www.gao.gov/products/{report_id}`
- PDF: `https://www.gao.gov/assets/{report_id}.pdf`

**Rate Limiting:**
- 2.5 seconds between requests
- Public domain, but respect site

**Quality Checks:**
- Report should be >30 pages
- PDF should match HTML content
- Verify it's a full report (not just highlights)

#### Strategy E: eLife Collection

**Reconnaissance:**
```python
# Test eLife API
import requests
base_url = "https://api.elifesciences.org/search"

params = {
    "for": "neuroscience",
    "page": 1,
    "per-page": 20,
    "sort": "date",
    "order": "desc",
    "type": "research-article"
}
response = requests.get(base_url, params=params)
```

**Discovery Method:**
1. Use eLife API to search recent research articles
2. Extract article IDs and DOIs
3. Download HTML: `elifesciences.org/articles/{article_id}`
4. Download PDF: `elifesciences.org/articles/{article_id}.pdf`

**URL Patterns:**
- HTML: `https://elifesciences.org/articles/{article_id}`
- PDF: `https://elifesciences.org/articles/{article_id}.pdf`

**Rate Limiting:**
- 2-3 seconds between requests
- Respectful crawling

**Quality Checks:**
- Verify HTML rendering quality
- Check for figures and supplementary materials
- PDF should be complete

---

## 📝 Collection Script Template (Adapted for Each Source)

```python
#!/usr/bin/env python3
"""
Collect HTML-PDF pairs from [SOURCE NAME]

Target: 30-50 pairs
Domain: [medical/science/engineering/government]
Document Type: [journal articles/preprints/reports]
"""

import requests
import time
from pathlib import Path
import sys

# Rate limiting
REQUEST_DELAY = 2.5  # seconds between requests

# Output directories
OUTPUT_DIR = Path("data/raw_html_pdf_pairs/[source_name]")
HTML_DIR = OUTPUT_DIR / "html"
PDF_DIR = OUTPUT_DIR / "pdf"
LOG_DIR = OUTPUT_DIR / "logs"

def setup_directories():
    """Create output directories if they don't exist."""
    for dir in [HTML_DIR, PDF_DIR, LOG_DIR]:
        dir.mkdir(parents=True, exist_ok=True)

def discover_articles(limit=50):
    """
    Discover articles using API or web scraping.

    Returns:
        list: Article metadata (ID, title, authors, URLs)
    """
    articles = []

    # [SOURCE-SPECIFIC IMPLEMENTATION]
    # Example for PMC:
    # base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    # params = {"db": "pmc", "term": "hasabstract", "retmax": limit}
    # response = requests.get(base_url, params=params)
    # ... parse and extract article IDs ...

    return articles

def download_html(article_id, output_path):
    """
    Download HTML version of article.

    Args:
        article_id: Unique identifier for article
        output_path: Where to save HTML file

    Returns:
        bool: Success status
    """
    try:
        # [SOURCE-SPECIFIC IMPLEMENTATION]
        # Example: requests.get(f"https://source.org/articles/{article_id}")

        time.sleep(REQUEST_DELAY)
        return True
    except Exception as e:
        print(f"Error downloading HTML for {article_id}: {e}")
        return False

def download_pdf(article_id, output_path):
    """
    Download PDF version of article.

    Args:
        article_id: Unique identifier for article
        output_path: Where to save PDF file

    Returns:
        bool: Success status
    """
    try:
        # [SOURCE-SPECIFIC IMPLEMENTATION]
        # Example: requests.get(f"https://source.org/articles/{article_id}.pdf")

        time.sleep(REQUEST_DELAY)
        return True
    except Exception as e:
        print(f"Error downloading PDF for {article_id}: {e}")
        return False

def validate_pair(html_path, pdf_path):
    """
    Verify HTML-PDF pairing quality.

    Args:
        html_path: Path to HTML file
        pdf_path: Path to PDF file

    Returns:
        dict: Validation results (file_sizes, word_counts, similarity, etc.)
    """
    validation = {
        "html_exists": html_path.exists(),
        "pdf_exists": pdf_path.exists(),
        "html_size": html_path.stat().st_size if html_path.exists() else 0,
        "pdf_size": pdf_path.stat().st_size if pdf_path.exists() else 0,
        "valid": False
    }

    # Check minimum file sizes
    if validation["html_size"] > 10000 and validation["pdf_size"] > 100000:
        validation["valid"] = True

    return validation

def generate_report(collected, failed):
    """Generate collection report with statistics."""
    report_path = LOG_DIR / "COLLECTION_REPORT.md"

    with open(report_path, 'w') as f:
        f.write(f"# [SOURCE NAME] Collection Report\n\n")
        f.write(f"**Date:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Target:** 30-50 pairs\n")
        f.write(f"**Achieved:** {len(collected)} pairs\n")
        f.write(f"**Failed:** {len(failed)} attempts\n\n")

        # ... detailed statistics ...

def main():
    """Main collection workflow."""
    print(f"Starting collection from [SOURCE NAME]...")
    print(f"Target: 30-50 HTML-PDF pairs")
    print()

    setup_directories()

    # Discovery
    print("Phase 1: Discovering articles...")
    articles = discover_articles(limit=50)
    print(f"Found {len(articles)} candidate articles")
    print()

    # Collection
    print("Phase 2: Downloading HTML-PDF pairs...")
    collected = []
    failed = []

    for i, article in enumerate(articles, 1):
        print(f"[{i}/{len(articles)}] Processing: {article['title'][:50]}...")

        # Construct file paths
        article_id = article['id']
        html_path = HTML_DIR / f"{article_id}.html"
        pdf_path = PDF_DIR / f"{article_id}.pdf"

        # Download files
        html_success = download_html(article_id, html_path)
        pdf_success = download_pdf(article_id, pdf_path)

        # Validate
        if html_success and pdf_success:
            validation = validate_pair(html_path, pdf_path)
            if validation["valid"]:
                collected.append(article)
                print(f"  ✓ Success")
            else:
                failed.append(article)
                print(f"  ✗ Validation failed")
        else:
            failed.append(article)
            print(f"  ✗ Download failed")

        # Stop if we have enough
        if len(collected) >= 50:
            print(f"\nTarget exceeded! Collected {len(collected)} pairs.")
            break

    # Reporting
    print()
    print("Phase 3: Generating report...")
    generate_report(collected, failed)

    print()
    print("="*60)
    print(f"COLLECTION COMPLETE")
    print(f"  Successful: {len(collected)} pairs")
    print(f"  Failed: {len(failed)} attempts")
    print(f"  Success rate: {100*len(collected)/(len(collected)+len(failed)):.1f}%")
    print("="*60)

if __name__ == "__main__":
    main()
```

---

## 🎯 Agent Deployment Plan

### Parallel Agent Strategy (5 agents, 1 week)

**Agent 1: PubMed Central Specialist**
- **Target:** 40 pairs
- **Focus:** Medical/biomedical articles
- **Categories:** Clinical trials, systematic reviews, basic research
- **Estimated time:** 1-2 days

**Agent 2: arXiv Specialist**
- **Target:** 40 pairs
- **Focus:** STEM preprints
- **Categories:** cs.AI, cs.LG, physics, math, econ
- **Estimated time:** 1-2 days

**Agent 3: PLOS Specialist**
- **Target:** 30 pairs
- **Focus:** Open access multidisciplinary
- **Journals:** PLOS ONE, Biology, Medicine, Computational Biology
- **Estimated time:** 1 day

**Agent 4: Government Documents Specialist**
- **Target:** 20 pairs
- **Focus:** GAO reports, policy documents
- **Topics:** Diverse (healthcare, defense, economy, environment)
- **Estimated time:** 1 day

**Agent 5: eLife Specialist**
- **Target:** 20 pairs
- **Focus:** High-quality biomedical research
- **Categories:** Neuroscience, genetics, cell biology, immunology
- **Estimated time:** 1 day

**Total Expected:** 150 pairs in 5-7 days

---

## 📊 Success Metrics & Reporting

### Required Metrics Per Agent

1. **Quantitative:**
   - Total pairs collected
   - Success rate (collected / attempted)
   - Average file sizes (HTML, PDF)
   - Time taken (collection speed)
   - Errors encountered

2. **Qualitative:**
   - Document structure diversity (single/multi-column, equations, figures)
   - Citation style coverage
   - Topic diversity within source
   - HTML-PDF alignment quality

3. **Technical:**
   - API rate limits respected
   - Blocking incidents (none expected)
   - File corruption (should be 0%)
   - Validation failures

### Report Template

Each agent produces:
- **COLLECTION_REPORT.md** - Detailed summary (like law review reports)
- **collected_articles.json** - Machine-readable metadata
- **progress.txt** - Real-time progress log

---

## 🚀 Next Steps

### Week 1: Rapid Collection
1. Deploy 5 parallel agents with source-specific instructions
2. Monitor progress daily
3. Adjust strategies if blocking occurs
4. Target: 150-180 pairs

### Week 2: Validation & Integration
1. Verify HTML-PDF text matching (>70% similarity)
2. Check structural elements (headings, figures, captions)
3. Remove low-quality pairs
4. Merge with existing law review corpus

### Week 3: Ready for Training
- Final corpus: 350-400 pairs
- Law reviews: ~40%
- Non-law: ~60%
- Train DoclingBERT v3.1

---

**Last Updated:** October 17, 2025
**Status:** Ready for agent deployment
