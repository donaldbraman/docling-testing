# Agent 1: PubMed Central (PMC) Collection Instructions

**Source:** PubMed Central (PMC) - https://www.ncbi.nlm.nih.gov/pmc/
**Target:** 40 medical/biomedical HTML-PDF pairs (stretch: 50)
**Domain:** Medical, biomedical, life sciences
**Estimated Time:** 1-2 days
**Priority:** HIGH (critical for corpus diversity)

---

## 🎯 Objective

Collect 40+ complete HTML-PDF pairs from PubMed Central open-access articles to add medical/biomedical document diversity to the training corpus.

**Why PMC:**
- Excellent HTML-PDF pairing (both provided by source)
- Diverse medical topics (clinical trials, systematic reviews, basic research)
- Multi-column layouts common
- Different citation style (Vancouver numbering)
- Complex figures with sub-panels
- Statistical tables and patient demographics
- Methods/Results/Discussion structure (different from law reviews)

---

## 🛠️ Stage 1: Reconnaissance (30 minutes)

### Phase 1A: API Documentation Review

**PMC E-utilities API:**
- **Base URL:** https://eutils.ncbi.nlm.nih.gov/entrez/eutils/
- **Documentation:** https://www.ncbi.nlm.nih.gov/books/NBK25501/
- **Rate Limit:** 3 requests/second (without API key), 10 req/s with key
- **No API key needed** for 40 articles (manageable with 3 req/s limit)

**Test API Connection:**
```bash
curl "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pmc&term=hasabstract%20AND%20ffrft[filter]&retmax=5&retmode=json"
```

Expected response: JSON with PMC IDs

### Phase 1B: URL Pattern Discovery

**HTML Pattern:**
- Format: `https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{ID}/`
- Example: `https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8765432/`

**PDF Pattern:**
- Format: `https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{ID}/pdf/`
- Example: `https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8765432/pdf/main.pdf`

**XML Pattern (for HTML conversion if needed):**
- Format: `https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{ID}/xml/`
- Standard: JATS XML format

### Phase 1C: Rate Limiting Setup

- **Delay:** 0.4 seconds between requests (2.5 req/s, under 3 req/s limit)
- **Extended pause:** 5-second break every 20 requests
- **User-Agent:** Include contact email for courtesy

---

## 🔄 Stage 2: Discovery Strategy

### Method: API-Based Search (RECOMMENDED)

**Step 1: Search for Recent Open-Access Articles**

Use E-utilities `esearch` to find PMC IDs:

```python
import requests
import time

base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

# Search for recent full-text open-access articles
search_url = f"{base_url}esearch.fcgi"
params = {
    "db": "pmc",
    "term": "hasabstract AND ffrft[filter] AND 2024[pdat]",  # 2024 articles
    "retmax": 100,  # Get 100 candidates (will collect 40-50)
    "retmode": "json",
    "sort": "pub_date",
    "email": "research@example.com"  # Replace with real contact
}

response = requests.get(search_url, params=params)
data = response.json()
pmc_ids = data['esearchresult']['idlist']

print(f"Found {len(pmc_ids)} candidate articles")
time.sleep(0.4)  # Rate limiting
```

**Step 2: Fetch Article Metadata**

Use `esummary` to get article details (title, authors, journal):

```python
# Fetch summaries in batches of 20
for i in range(0, len(pmc_ids), 20):
    batch_ids = pmc_ids[i:i+20]
    id_str = ','.join(batch_ids)

    summary_url = f"{base_url}esummary.fcgi"
    params = {
        "db": "pmc",
        "id": id_str,
        "retmode": "json"
    }

    response = requests.get(summary_url, params=params)
    summaries = response.json()

    # Extract article info
    for pmc_id in batch_ids:
        article_info = summaries['result'][pmc_id]
        # Store: title, authors, journal, pub_date

    time.sleep(0.4)  # Rate limiting
```

**Step 3: Download HTML and PDF**

For each PMC ID:
1. Construct HTML URL: `https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{id}/`
2. Construct PDF URL: `https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{id}/pdf/`
3. Download both files
4. Validate file quality

```python
def download_pmc_pair(pmc_id, output_dir):
    """Download HTML and PDF for PMC article."""
    html_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmc_id}/"
    pdf_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmc_id}/pdf/"

    # Download HTML
    html_response = requests.get(html_url)
    if html_response.status_code == 200:
        html_path = output_dir / f"pmc_{pmc_id}.html"
        html_path.write_text(html_response.text)

    time.sleep(0.4)  # Rate limiting

    # Download PDF
    pdf_response = requests.get(pdf_url)
    if pdf_response.status_code == 200:
        pdf_path = output_dir / f"pmc_{pmc_id}.pdf"
        pdf_path.write_bytes(pdf_response.content)

    time.sleep(0.4)  # Rate limiting

    return True
```

---

## ✅ Stage 3: Collection Execution

### Pre-Collection Checklist

- [ ] PMC API accessible (test with curl)
- [ ] Output directories created (`data/raw_html/`, `data/raw_pdf/`)
- [ ] Collection log directory created (`data/collection_logs/pubmed_central/`)
- [ ] Python environment ready (uv run python)
- [ ] Rate limiting confirmed (0.4s delay)

### Collection Process

**Use Provided Script:**
```bash
cd /Users/donaldbraman/Documents/GitHub/docling-testing
uv run python scripts/data_collection/collect_pubmed_central.py --target 50
```

**Or Manual Collection (if script needs adjustment):**
1. Run API search to get PMC IDs
2. For each PMC ID:
   - Download HTML
   - Download PDF
   - Validate both files exist and are >10KB (HTML) and >100KB (PDF)
   - Log success/failure
   - Rate limit: wait 0.4s
3. Stop when 40+ successful pairs collected

### Real-Time Monitoring

**Progress Tracking:**
```bash
# Watch progress log
tail -f data/collection_logs/pubmed_central/progress.txt

# Count collected files
ls data/raw_html/pmc_*.html | wc -l
ls data/raw_pdf/pmc_*.pdf | wc -l
```

**Expected Progress:**
- 40 pairs in ~60-80 API calls (search + summaries + downloads)
- With 0.4s delays: ~24-32 seconds of wait time
- Total time: 5-10 minutes for downloads + processing

---

## 🎯 Stage 4: Verification & Quality Control

### File Validation

**Check Each Pair:**
1. **HTML file size:** >10,000 bytes (full article, not just abstract)
2. **PDF file size:** >100,000 bytes (>5 pages estimated)
3. **HTML structure:** Contains `<article>` or full-text content
4. **PDF validity:** Can be opened (use pypdf to verify)

**Validation Script:**
```python
import pypdf
from pathlib import Path

def validate_pmc_pair(html_path, pdf_path):
    """Validate HTML-PDF pair quality."""
    checks = {
        "html_exists": html_path.exists(),
        "pdf_exists": pdf_path.exists(),
        "html_size_ok": html_path.stat().st_size > 10000,
        "pdf_size_ok": pdf_path.stat().st_size > 100000,
        "pdf_readable": False
    }

    # Try to open PDF
    try:
        with open(pdf_path, 'rb') as f:
            reader = pypdf.PdfReader(f)
            checks["pdf_readable"] = len(reader.pages) > 3
    except:
        pass

    checks["valid"] = all(checks.values())
    return checks
```

### Diversity Check

**Verify Medical Topic Diversity:**
- At least 5 different journals represented
- At least 3 different medical subfields (e.g., oncology, cardiology, neurology)
- Mix of article types: research articles, systematic reviews, clinical trials

**Check via titles:**
```python
# Review collected article titles
titles = [article['title'] for article in collected_articles]

# Ensure diversity (not all from one narrow topic)
# Example: Not all "COVID-19" papers - need variety
```

---

## 📊 Stage 5: Reporting

### Required Report: `data/collection_logs/pubmed_central/COLLECTION_REPORT.md`

**Report Structure** (following law review pattern):

```markdown
# PubMed Central Collection Report

**Date:** [Date]
**Source:** PubMed Central (PMC)
**Target:** 40-50 pairs
**Achieved:** [X] complete pairs

## Collection Results

### Success Metrics
- Target: 40 pairs minimum
- Achieved: [X] complete pairs ([Y]% of target)
- Success Rate: [X]/[Y] attempted ([Z]%)

### Files Collected
- HTML files: [X] articles (avg size: [Y] KB)
- PDF files: [X] matching PDFs (avg size: [Y] MB)
- Total data: [X] MB

## Discovery Strategy

### API Query Used
- Database: PMC
- Search term: hasabstract AND ffrft[filter] AND 2024[pdat]
- Results returned: [X] candidates
- Selected: [X] for download

### Collection Process
- Method: PMC E-utilities API
- Rate limiting: 0.4s between requests
- Total time: [X] minutes
- Errors: [X] (detail below)

## Articles Collected

[List of 40+ articles with titles, PMC IDs, topics]

1. PMC123456: "Title of Article" - Journal - Topic
2. PMC123457: "Title of Article" - Journal - Topic
...

## Diversity Analysis

### Journals Represented
- [Journal 1]: [X] articles
- [Journal 2]: [X] articles
...

### Medical Subfields
- Oncology: [X] articles
- Cardiology: [X] articles
- Neurology: [X] articles
...

### Article Types
- Research Articles: [X]
- Systematic Reviews: [X]
- Clinical Trials: [X]

## Technical Details

### File Locations
- HTML: `/Users/donaldbraman/Documents/GitHub/docling-testing/data/raw_html/`
- PDF: `/Users/donaldbraman/Documents/GitHub/docling-testing/data/raw_pdf/`
- Logs: `/Users/donaldbraman/Documents/GitHub/docling-testing/data/collection_logs/pubmed_central/`

### Naming Convention
- HTML: `pmc_{PMC_ID}.html`
- PDF: `pmc_{PMC_ID}.pdf`

### Quality Verification
- All HTML files contain full text (verified by size check)
- All PDFs are valid and complete
- No 403/429 errors encountered
- No corrupted files

## Compliance & Ethics

### Rate Limiting
- Delay: 0.4 seconds between requests (2.5 req/s)
- Extended pauses: 5s every 20 requests
- Total requests: ~[X] (within PMC guidelines)

### Data Use
- Purpose: ML training corpus for document classification
- Use case: Training models to identify document structure
- Compliance: Open access articles only
- Attribution: PMC properly cited

## Success Criteria Check

- ✓ Minimum 40 complete pairs: [✓/✗]
- ✓ All articles full text (>5k words): [✓/✗]
- ✓ Files readable and valid: [✓/✗]
- ✓ No blocking: [✓/✗]
- ✓ Diverse medical topics: [✓/✗]
- ✓ Progress documented: [✓/✗]

## Next Steps

1. Validate HTML-PDF content alignment
2. Add to training corpus
3. Verify medical formatting patterns are captured
```

### Additional Files

**`collected_articles.json`:**
```json
[
  {
    "pmc_id": "PMC12345678",
    "title": "Article Title",
    "authors": ["Author 1", "Author 2"],
    "journal": "Journal Name",
    "pub_date": "2024-03-15",
    "html_path": "data/raw_html/pmc_12345678.html",
    "pdf_path": "data/raw_pdf/pmc_12345678.pdf",
    "html_size": 123456,
    "pdf_size": 987654,
    "validated": true
  }
]
```

**`progress.txt`:** Real-time log of collection process

---

## ⚠️ Troubleshooting

### Issue: 403 Forbidden errors

**Cause:** Aggressive crawling or missing user-agent
**Solution:**
- Add polite user-agent with contact email
- Increase delay to 1 second
- Use PMC's bulk FTP if many 403s (for larger collections)

### Issue: XML instead of HTML

**Cause:** Some PMC articles only have JATS XML
**Solution:**
- Download XML and convert to HTML using lxml
- Or accept XML as "HTML" (it's structured text)
- Script handles this automatically

### Issue: PDF not found (404)

**Cause:** Some articles don't have PDF versions
**Solution:**
- Skip article and move to next candidate
- Log as "PDF not available"
- Not counted toward success metrics

### Issue: Rate limiting (429 errors)

**Cause:** Too many requests too fast
**Solution:**
- Increase delay to 1 second
- Add longer pauses (10s every 20 requests)
- Consider getting NCBI API key (allows 10 req/s)

---

## ✅ Success Criteria Summary

**Minimum Requirements:**
- [ ] 40+ complete HTML-PDF pairs collected
- [ ] All pairs from recent open-access articles (2024-2025)
- [ ] Diverse medical topics (5+ journals, 3+ subfields)
- [ ] Files validated (correct sizes, readable)
- [ ] No blocking incidents
- [ ] Comprehensive collection report completed

**Quality Indicators:**
- [ ] Multi-column layouts present (common in medical journals)
- [ ] Complex figures with sub-panels
- [ ] Statistical tables present
- [ ] Vancouver citation style (numbered references)
- [ ] Methods/Results/Discussion structure

---

## 📞 Support

**If you encounter issues:**
1. Check PMC API status: https://www.ncbi.nlm.nih.gov/pmc/
2. Review E-utilities documentation: https://www.ncbi.nlm.nih.gov/books/NBK25501/
3. Consult collection script comments
4. Log detailed error messages for debugging

**Contact for PMC-specific questions:**
- NCBI Help Desk: https://support.ncbi.nlm.nih.gov/

---

**Agent Status:** READY TO DEPLOY
**Estimated Completion:** 1-2 days
**Next Agent:** Agent 2 (arXiv)
