# Law Review Collection & Validation Skill

**Purpose:** Automatically collect HTML-PDF pairs from law review websites with quality validation (≥75% Jaccard similarity).

## Your Role

You are a specialized law review collection agent. Your job is to:
1. Collect HTML-PDF pairs from a specified law review source
2. Validate quality using Jaccard similarity matching
3. Only keep pairs with ≥75% similarity
4. Report results and maintain clean corpus

## Current Corpus Status

**Well-represented (skip these):**
- Texas Law Review: 11 pairs ✅
- California Law Review: 10 pairs ✅
- USC Law Review: 9 pairs ✅
- BU Law Review: 3 pairs ✅

**PRIORITY: Underrepresented Journals (collect from these)**

**Tier 1 - Has some pairs, need more (1-2 pairs):**
- Harvard Law Review: 1 pair → **Target: 5-8 more** → `scripts/data_collection/scrape_harvard_simple.py`
- Wisconsin Law Review: 1 pair → **Target: 5-8 more** → (check for collection script)
- Chicago Law Review: 2 pairs → **Target: 5-8 more** → `scripts/data_collection/scrape_chicago_law_review.py`

**Tier 2 - Not represented yet (0 pairs):**
- Michigan Law Review: 0 pairs → **Target: 8-10** → `scripts/data_collection/scrape_michigan.py`
- Stanford Law Review: 0 pairs → **Target: 8-10** → `scripts/data_collection/download_stanford_law_review.py`
- Columbia Law Review: 0 pairs → **Target: 8-10** → `scripts/data_collection/scrape_columbia.py`
- Virginia Law Review: 0 pairs → **Target: 8-10** → `scripts/data_collection/scrape_virginia_law_review.py`
- Northwestern Law Review: 0 pairs → **Target: 8-10** → `scripts/data_collection/scrape_northwestern_law_review.py`
- Indiana Law Journal: 0 pairs → **Target: 8-10** → `scripts/data_collection/collect_indiana_law_journal.py`

**Note:** Focus on Tier 2 first to maximize diversity. Skip well-represented journals.

## Workflow

### Phase 1: Collection
1. Ask user which law review source to collect from (or use all available)
2. Run the appropriate collection script(s)
3. Monitor progress and handle errors
4. Report: number of HTML-PDF pairs collected

### Phase 2: Quality Validation
1. For each collected pair, calculate Jaccard similarity using the validation code below
2. Categorize pairs:
   - **Excellent (≥90%)**: Ideal matches
   - **Good (75-90%)**: Acceptable matches
   - **Poor (<75%)**: Reject and archive

### Phase 3: Cleanup
1. Archive pairs with <75% similarity to `data/archived_low_quality/`
2. Move good pairs (≥75%) to `data/raw_html/` and `data/raw_pdf/`
3. Generate quality report showing:
   - Total collected
   - Accepted (≥75%)
   - Rejected (<75%)
   - Average Jaccard score
   - Distribution histogram

## Validation Code Template

Use this code to validate pairs:

```python
import re
from pathlib import Path
from bs4 import BeautifulSoup
import pypdf

def normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\d+", "", text)
    return text.strip()

def get_word_set(text: str, min_length: int = 4) -> set:
    """Get set of significant words from text."""
    words = text.split()
    return {w for w in words if len(w) >= min_length}

def extract_text_from_html(html_path: Path) -> str:
    """Extract clean text from HTML file."""
    with open(html_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    for script in soup(["script", "style"]):
        script.decompose()

    text = soup.get_text()
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = " ".join(chunk for chunk in chunks if chunk)
    return text.lower()

def calculate_jaccard(html_path: Path, pdf_path: Path) -> float:
    """Calculate Jaccard similarity between HTML and PDF."""
    # Extract HTML text
    html_text = extract_text_from_html(html_path)

    # Extract PDF text
    pdf_reader = pypdf.PdfReader(pdf_path)
    pdf_text = ""
    for page in pdf_reader.pages:
        pdf_text += page.extract_text()
    pdf_text = pdf_text.lower()

    # Normalize
    html_norm = normalize_text(html_text)
    pdf_norm = normalize_text(pdf_text)

    # Get word sets
    html_words = get_word_set(html_norm)
    pdf_words = get_word_set(pdf_norm)

    if not html_words or not pdf_words:
        return 0.0

    # Calculate Jaccard
    intersection = html_words & pdf_words
    union = html_words | pdf_words
    return (len(intersection) / len(union)) * 100 if union else 0.0
```

## Quality Thresholds

- **≥90%**: Excellent - full-text HTML perfectly matches PDF
- **75-90%**: Good - full-text HTML with minor differences
- **60-75%**: Marginal - may have missing content, use with caution
- **<60%**: Poor - likely abstract-only or mismatched content
- **<40%**: Very Poor - definitely abstract-only or wrong pairing

**This skill requires ≥75% for acceptance.**

## Output Report Format

After collection and validation, provide a report like this:

```markdown
# Law Review Collection Report

**Source:** [Law Review Name]
**Date:** [Date]

## Collection Results

- Total pairs collected: X
- Accepted (≥75%): Y
- Rejected (<75%): Z

## Quality Distribution

- Excellent (≥90%): N pairs (average: XX.X%)
- Good (75-90%): N pairs (average: XX.X%)
- Rejected (<75%): N pairs (average: XX.X%)

## Top 10 Pairs

1. XX.X% - [article title/basename]
2. XX.X% - [article title/basename]
...

## Files

- Accepted pairs: `data/raw_html/` and `data/raw_pdf/`
- Rejected pairs: `data/archived_low_quality/`
- Full results: `data/collection_logs/[source]/validation_results.csv`
```

## Important Notes

1. **Always validate before accepting** - Don't assume HTML files contain full text
2. **Archive low-quality pairs** - Don't delete, user may want to review
3. **Check for duplicates** - Compare against existing corpus basenames
4. **Handle errors gracefully** - Some PDFs may be corrupted or protected
5. **Respect rate limits** - Add delays between requests (1-2 seconds)
6. **Save intermediate results** - Don't lose work if validation fails partway

## Success Criteria

A successful collection run should:
- Collect at least 10 new pairs
- Achieve ≥50% acceptance rate (≥75% Jaccard)
- Have average accepted score ≥85%
- No errors or crashes
- Generate complete documentation

## Files to Create

For each collection run, create:
1. `data/collection_logs/[source]_[date]/COLLECTION_REPORT.md` - Summary report
2. `data/collection_logs/[source]_[date]/validation_results.csv` - All scores
3. `data/collection_logs/[source]_[date]/rejected_pairs.txt` - List of rejected basenames

## Next Steps After Collection

Once you've collected and validated pairs:
1. Report results to user
2. Ask if they want to collect from another source
3. Suggest running corpus analysis to see updated statistics
4. Note: User will handle training data generation separately

---

Remember: Quality over quantity. It's better to have 20 excellent pairs than 100 poor ones!
