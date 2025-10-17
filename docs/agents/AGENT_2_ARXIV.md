# Agent 2: arXiv Collection Instructions

**Source:** arXiv + ar5iv - https://arxiv.org + https://ar5iv.org
**Target:** 40 STEM preprint HTML-PDF pairs (stretch: 50)
**Domain:** Computer Science, Physics, Mathematics, Economics
**Estimated Time:** 1-2 days
**Priority:** HIGH (critical for STEM diversity)

---

## 🎯 Objective

Collect 40+ complete HTML-PDF pairs from arXiv preprints to add STEM document diversity with heavy equations, algorithms, and LaTeX-derived formatting.

**Why arXiv:**
- LaTeX source → HTML (different from native HTML)
- Heavy equations and mathematical notation
- Algorithm pseudocode blocks
- Multi-domain coverage (CS, physics, math, econ)
- Different structural patterns than academic journals
- Pre-print format (less polished, more experimental)

---

## 🛠️ Stage 1: Reconnaissance (20 minutes)

### arXiv API Documentation

**API Endpoint:** http://export.arxiv.org/api/query
**Documentation:** https://info.arxiv.org/help/api/index.html
**Rate Limit:** 1 request per 3 seconds (strictly enforced)
**Response Format:** Atom XML

**Test API:**
```bash
curl "http://export.arxiv.org/api/query?search_query=cat:cs.AI&start=0&max_results=5"
```

### URL Patterns

**PDF:**
- Format: `https://arxiv.org/pdf/{arxiv_id}.pdf`
- Example: `https://arxiv.org/pdf/2401.12345.pdf`

**HTML (ar5iv - LaTeX to HTML):**
- Format: `https://ar5iv.org/html/{arxiv_id}`
- Example: `https://ar5iv.org/html/2401.12345`
- Note: Third-party service that renders LaTeX → HTML

**Alternative HTML (new arXiv HTML):**
- Format: `https://arxiv.org/html/{arxiv_id}`
- Note: Newer, not all papers have this yet

### Rate Limiting Setup

- **Delay:** 3 seconds between API requests (mandatory)
- **PDF downloads:** 2 seconds between (be respectful)
- **Total for 40 papers:** ~3-5 minutes of wait time

---

## 🔄 Stage 2: Discovery Strategy

### Method: API-Based Category Search

**Step 1: Search Recent Papers by Category**

Query multiple categories to ensure diversity:

```python
import requests
import time
from xml.etree import ElementTree

base_url = "http://export.arxiv.org/api/query"

# Diverse categories
categories = [
    "cs.AI",     # Artificial Intelligence
    "cs.LG",     # Machine Learning
    "cs.CL",     # Computation and Language
    "physics.comp-ph",  # Computational Physics
    "math.ST",   # Statistics Theory
    "econ.GN",   # General Economics
]

all_papers = []

for category in categories:
    params = {
        "search_query": f"cat:{category} AND submittedDate:[202401* TO 202412*]",
        "start": 0,
        "max_results": 10,  # 10 per category = 60 total candidates
        "sortBy": "submittedDate",
        "sortOrder": "descending"
    }

    response = requests.get(base_url, params=params)
    time.sleep(3)  # MANDATORY 3-second delay

    # Parse Atom XML
    root = ElementTree.fromstring(response.content)
    # Extract: id, title, authors, summary, published date

print(f"Found {len(all_papers)} candidate papers across {len(categories)} categories")
```

**Step 2: Extract arXiv IDs**

From Atom XML, extract arXiv IDs:
```python
# Example arXiv ID formats:
# - 2401.12345 (new format, year + month + sequence)
# - 1901.00001 (older format)

def extract_arxiv_id(entry_id):
    """Extract arXiv ID from entry URL."""
    # entry_id format: http://arxiv.org/abs/2401.12345v1
    return entry_id.split('/abs/')[-1].replace('v1', '').replace('v2', '')
```

**Step 3: Download PDFs and HTML**

```python
def download_arxiv_pair(arxiv_id, output_dir):
    """Download PDF from arXiv and HTML from ar5iv."""

    # Download PDF
    pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
    pdf_response = requests.get(pdf_url)
    if pdf_response.status_code == 200:
        pdf_path = output_dir / f"arxiv_{arxiv_id.replace('.', '_')}.pdf"
        pdf_path.write_bytes(pdf_response.content)

    time.sleep(2)  # Be respectful

    # Download HTML from ar5iv (LaTeX rendering)
    html_url = f"https://ar5iv.org/html/{arxiv_id}"
    html_response = requests.get(html_url)
    if html_response.status_code == 200:
        html_path = output_dir / f"arxiv_{arxiv_id.replace('.', '_')}.html"
        html_path.write_text(html_response.text)

    time.sleep(2)  # Be respectful

    return True
```

---

## ✅ Stage 3: Collection Execution

### Pre-Collection Checklist

- [ ] arXiv API accessible
- [ ] ar5iv.org accessible (test one paper)
- [ ] Output directories created
- [ ] Rate limiting confirmed (3s for API, 2s for downloads)

### Collection Process

**Use Provided Script:**
```bash
cd /Users/donaldbraman/Documents/GitHub/docling-testing
uv run python scripts/data_collection/collect_arxiv_papers.py --target 50
```

**Target Distribution:**
- cs.AI: 8-10 papers
- cs.LG: 8-10 papers
- cs.CL: 6-8 papers
- physics: 6-8 papers
- math: 4-6 papers
- econ: 4-6 papers

### Quality Checks During Collection

**Verify HTML Rendering:**
- Equations rendered properly (check for LaTeX math)
- Figures present
- Code blocks formatted
- Not just abstract

**Verify PDF:**
- Complete paper (>5 pages)
- Figures visible
- Equations readable

---

## 📊 Stage 4: Verification

### HTML Quality Check

**ar5iv HTML should have:**
- Rendered equations (check for `<math>` tags or MathML)
- Code listings (if applicable)
- Figure references
- Bibliography

**If HTML rendering poor:**
- Try alternative: `https://arxiv.org/html/{arxiv_id}`
- Or skip paper and get next candidate

### Diversity Verification

**Ensure variety:**
- At least 4 different categories represented
- Mix of theoretical and applied papers
- Range of paper lengths (15-50 pages)
- Various domains (AI, physics, math, econ)

---

## 📊 Stage 5: Reporting

### Required Report: `data/collection_logs/arxiv/COLLECTION_REPORT.md`

**Key Sections:**
1. Collection summary (target vs achieved)
2. Category distribution
3. Sample of collected papers (titles, IDs, topics)
4. HTML rendering quality assessment
5. Technical details (rate limiting, errors)
6. Success criteria checklist

---

## ⚠️ Troubleshooting

### Issue: ar5iv HTML rendering fails

**Solution:** Try native arXiv HTML: `https://arxiv.org/html/{arxiv_id}`

### Issue: 403 from ar5iv

**Solution:** Add user-agent, increase delay to 3 seconds

### Issue: Papers too short (letters, comments)

**Solution:** Filter by page count in PDF (>10 pages), or check abstract length

---

## ✅ Success Criteria

**Minimum:**
- [ ] 40+ complete pairs
- [ ] 4+ categories represented
- [ ] Equations visible in HTML
- [ ] PDFs complete (>10 pages each)
- [ ] No blocking incidents

**Quality:**
- [ ] LaTeX rendering quality verified
- [ ] Mathematical notation present
- [ ] Algorithm pseudocode (where applicable)
- [ ] Diverse STEM domains

---

**Agent Status:** READY TO DEPLOY
**Estimated Time:** 1-2 days
**Next Agent:** Agent 3 (PLOS)
