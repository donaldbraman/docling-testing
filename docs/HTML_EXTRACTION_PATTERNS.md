# HTML Extraction Patterns for Law Reviews

## Summary

Investigation of HTML structure across 7 law reviews reveals **diverse patterns** requiring multi-strategy extraction.

**Critical Finding**: Current code only extracts simple `<p>` tags, missing 80%+ of content.

## Pattern Categories

### ✅ Pattern 1: Columbia Law Review - Inline Citation Footnotes
**Files**: `columbia_law_review_*.html`

**Body Text**: Standard `<p>` tags
**Footnote Pattern**: Inline `<cite class="footnote">` tags with nested content

```html
<cite class="footnote footnote-1 footnote-long">
    <span class="footnote-text">
        <span class="aside-footnote-count">1</span>
        [Footnote text content]
    </span>
</cite>
```

**Extraction Strategy**:
```python
for cite in soup.find_all('cite', class_='footnote'):
    text_span = cite.find('span', class_='footnote-text')
    if text_span:
        footnote_text = text_span.get_text(strip=True)
```

**Test Results**: 69 footnotes found in one article (vs 0 before)

---

### ✅ Pattern 2: Harvard Law Review - Separate Footnotes List
**Files**: `harvard_law_review_*.html`

**Body Text**: Standard `<p>` tags
**Footnote Pattern**: Separate section with list items

```html
<!-- Inline reference in body -->
<sup id="footnote-1" class="footnote-item">
    <a href="#footnote-ref-1">1</a>
</sup>

<!-- Footnote content at bottom -->
<li id="footnote-ref-1" class="single-article-footnotes-list__item">
    <div class="single-article-footnotes-list__item-inner">
        <p class="single-article-footnotes-list__item-content">
            [Footnote text content]
        </p>
    </div>
</li>
```

**Extraction Strategy**:
```python
for li in soup.find_all('li', id=re.compile(r'footnote-ref-\d+')):
    content = li.find('p', class_='single-article-footnotes-list__item-content')
    if content:
        footnote_text = content.get_text(strip=True)
```

**Test Results**: 155 footnotes found in one article (vs 0 before)

---

### ✅ Pattern 3: Michigan Law Review - Modern Footnotes Plugin
**Files**: `michigan_law_review_*.html`

**Statistics**:
- 66-235 `<p>` tags per article
- 134-372 `<sup>` markers per article
- 134-372 footnote spans per article

**Body Text**: Standard `<p>` tags (well-structured)
**Footnote Pattern**: `<span class="modern-footnotes-footnote__note">` with `data-mfn` attribute

```html
<!-- Inline reference in body -->
<sup class="modern-footnotes-footnote" data-mfn="1">
    <a aria-describedby="mfn-content-...-1" href="javascript:void(0)">1</a>
</sup>

<!-- Footnote content (rendered in HTML) -->
<span class="modern-footnotes-footnote__note"
      data-mfn="1"
      id="mfn-content-...-1"
      role="tooltip">
    Mapp v. Ohio, 367 U.S. 643, 645 (1961).
</span>
```

**Extraction Strategy**:
```python
for span in soup.find_all('span', class_='modern-footnotes-footnote__note'):
    footnote_text = span.get_text(strip=True)
```

**Test Results**: 372 footnotes found in one article

---

### ⚠️ Pattern 4: Duke Law Journal - Minimal Static Content
**Files**: `duke_law_journal_*.html`

**Statistics**: Only 12-14 `<p>` tags per article, 0 footnotes

**Issue**: JavaScript-rendered content (partial)
**Impact**: Low extraction rate (10-15 paragraphs vs expected 100+)

**Recommendation**: May need JavaScript rendering (Playwright) or alternative source

---

### ❌ Pattern 5: Georgetown Law Journal - JavaScript-Rendered
**Files**: `georgetown_law_journal_*.html`

**Statistics**: Only 4 `<p>` tags total, 0 footnotes

**Issue**: Fully JavaScript-rendered content
**Impact**: Virtually no extraction

**Evidence**:
```html
<section class="abstract_alt js-abstract-with-footnotes">
    <div class="abstract_alt_description js-footnotes-content">
```

**Recommendation**: Exclude from corpus OR use Playwright

---

### ❌ Pattern 6: Stanford Law Review - JavaScript-Rendered
**Files**: `stanford_law_review_*.html`

**Statistics**: 0 `<p>` tags, 0 footnotes

**Issue**: Fully JavaScript-rendered content
**Impact**: No extraction

**Recommendation**: Exclude from corpus OR use Playwright

---

## Corpus Quality Analysis

### Current Extraction (Broken)
- **32 pairs processed** (14 skipped by quality filter)
- **763 total paragraphs** (down from 1,260 in first run!)
- **47 footnotes** (6.2%) - severely under-represented
- **Many files showing 0 paragraphs** from PDF extraction

### Expected with Fixed Extraction

**Usable Law Reviews (Static HTML)**:
- Columbia: 9 articles × ~70 footnotes = ~630 footnotes
- Harvard: 10 articles × ~155 footnotes = ~1,550 footnotes
- Michigan: 5 articles × ~300 footnotes = ~1,500 footnotes

**Total Expected**: ~3,680 footnotes from 24 articles

**Unusable (JavaScript-rendered)**:
- Georgetown: 5 articles (4 `<p>` tags each)
- Duke: 5 articles (12-14 `<p>` tags each)
- Stanford: 8 articles (0 `<p>` tags each)

**Recommendation**: Focus on Columbia + Harvard + Michigan = ~3,680 high-quality footnotes

---

## Implementation Plan

### Phase 1: Update extract_from_html()
Add pattern-specific extraction to `match_html_pdf.py`:

```python
def extract_from_html(html_file: Path) -> List[Paragraph]:
    # ... existing encoding handling ...

    paragraphs = []

    # Pattern 1: Columbia inline footnotes
    for cite in soup.find_all('cite', class_='footnote'):
        text_span = cite.find('span', class_='footnote-text')
        if text_span:
            text = normalize_text(text_span.get_text())
            text = re.sub(r'^\d+[\.\s]+', '', text)  # Remove number prefix
            if len(text) > 20:
                paragraphs.append(Paragraph(
                    text=text,
                    label='footnote',
                    source='html',
                    original_index=len(paragraphs)
                ))

    # Pattern 2: Harvard list footnotes
    for li in soup.find_all('li', id=re.compile(r'footnote-ref-\d+')):
        content = li.find('p', class_='single-article-footnotes-list__item-content')
        if content:
            text = normalize_text(content.get_text())
            text = re.sub(r'^\d+[\.\s]+', '', text)
            if len(text) > 20:
                paragraphs.append(Paragraph(
                    text=text,
                    label='footnote',
                    source='html',
                    original_index=len(paragraphs)
                ))

    # Pattern 3: Michigan modern-footnotes
    for span in soup.find_all('span', class_='modern-footnotes-footnote__note'):
        text = normalize_text(span.get_text())
        if len(text) > 20:
            paragraphs.append(Paragraph(
                text=text,
                label='footnote',
                source='html',
                original_index=len(paragraphs)
            ))

    # Body text: <p> tags not in footnote containers
    # ... existing body text extraction ...

    return paragraphs
```

### Phase 2: Quality Filter
Skip JavaScript-rendered sources:
```python
# Detect JavaScript-rendered content
if len(soup.find_all('p')) < 20:  # Threshold for static content
    print(f"  ⚠️  Skipping {html_file.name}: JavaScript-rendered content")
    return []
```

### Phase 3: Re-run Label Transfer
- Use cached PDF extractions (already done)
- Expected: ~3,000-5,000 paragraphs with 20-30% footnotes
- Processing time: ~5 minutes (with caching)

---

## Next Steps

1. ✅ Document patterns (this file)
2. Update `match_html_pdf.py` with multi-pattern extraction
3. Re-run label transfer with caching
4. Analyze final corpus quality
5. Start ModernBERT training

---

**Last Updated**: 2025-10-14
**Investigation**: Issues #4, #5
