#!/usr/bin/env python3
"""
Extract HTML content using POSITIVE INCLUSION strategy.

Instead of filtering out unwanted content, this script ONLY extracts content
that has definitive structural markers for body text or footnotes.

This approach is more robust and less brittle than text-based exclusion filters.
"""

import json
import re
from pathlib import Path

from bs4 import BeautifulSoup

LABELED_HTML_DIR = Path("data/v3_data/processed_html")  # V3 pipeline output


def normalize_text(text: str) -> str:
    """Normalize text for consistency."""
    text = re.sub(r"\s+", " ", text)  # Collapse whitespace
    text = re.sub(r"-\s+", "", text)  # Remove line-break hyphens
    return text.strip()


def identify_journal(filename: str, soup: BeautifulSoup = None) -> str:
    """
    Identify journal from filename or HTML content.

    Args:
        filename: HTML filename
        soup: BeautifulSoup object (optional, will check HTML content if provided)

    Returns:
        Journal name string
    """
    # First try filename-based identification (fast)
    lower = filename.lower()
    if "bu_law_review" in lower or "bu law review" in lower:
        return "BU Law Review"
    elif "michigan_law_review" in lower:
        return "Michigan Law Review"
    elif "supreme_court_review" in lower:
        return "Supreme Court Review"
    elif "columbia" in lower and "law review" in lower:
        return "Columbia Law Review"
    elif "usc_law_review" in lower:
        return "USC Law Review"
    elif "harvard_law_review" in lower:
        return "Harvard Law Review"
    elif "texas" in lower and "law review" in lower:
        return "Texas Law Review"
    elif "california_law_review" in lower:
        return "California Law Review"
    elif "wisconsin_law_review" in lower:
        return "Wisconsin Law Review"
    elif "virginia_law_review" in lower:
        return "Virginia Law Review"
    elif "penn" in lower or "pennsylvania" in lower:
        return "Penn Law Review"
    elif "chicago" in lower:
        return "University of Chicago Law Review"
    elif "ucla" in lower:
        return "UCLA Law Review"

    # If no match and soup provided, check HTML content
    if soup:
        # Check title tag
        title_tag = soup.find("title")
        if title_tag:
            title = title_tag.get_text().lower()
            if "wisconsin law review" in title:
                return "Wisconsin Law Review"
            elif "columbia law review" in title:
                return "Columbia Law Review"
            elif "virginia law review" in title:
                return "Virginia Law Review"
            elif "texas law review" in title:
                return "Texas Law Review"
            elif "california law review" in title:
                return "California Law Review"
            elif "harvard law review" in title:
                return "Harvard Law Review"
            elif "penn" in title or "pennsylvania law review" in title:
                return "Penn Law Review"
            elif "bu law review" in title or "boston university" in title:
                return "BU Law Review"
            elif "michigan law review" in title:
                return "Michigan Law Review"
            elif "usc law review" in title or "southern california law review" in title:
                return "USC Law Review"
            elif "supreme court review" in title:
                return "Supreme Court Review"
            elif "chicago law review" in title:
                return "University of Chicago Law Review"
            elif "ucla law review" in title:
                return "UCLA Law Review"

        # Check meta tags
        meta_publisher = soup.find("meta", property="og:site_name")
        if meta_publisher:
            publisher = meta_publisher.get("content", "").lower()
            if "wisconsin law review" in publisher:
                return "Wisconsin Law Review"
            elif "columbia law review" in publisher:
                return "Columbia Law Review"
            elif "virginia law review" in publisher:
                return "Virginia Law Review"
            elif "texas law review" in publisher:
                return "Texas Law Review"
            elif "california law review" in publisher:
                return "California Law Review"

    return "Unknown"


def extract_bu_law_review_positive(soup: BeautifulSoup) -> tuple[list[str], list[str]]:
    """
    Extract BU Law Review using PURE POSITIVE INCLUSION.

    Definitive markers:
    - Body text: <p> tags inside <article> that DON'T start with [N]
    - Footnotes: <p> tags that start with [N] pattern

    NO exclusion filters - if it's a <p> tag in <article>, include it.
    Only skip truly empty paragraphs (whitespace only).
    """
    body = []
    footnotes = []

    # Find the article container (definitive body text container)
    article = soup.find("article")
    if not article:
        print("    ⚠️  No <article> tag found for BU Law Review")
        return body, footnotes

    # Extract ALL <p> tags from article (pure positive inclusion)
    for p in article.find_all("p"):
        text = p.get_text(separator=" ", strip=True)

        # Skip ONLY truly empty paragraphs (no content)
        if not text or len(text) == 0:
            continue

        normalized = normalize_text(text)

        # Check for definitive footnote marker: [N] at start
        if re.match(r"^\[\d+\]", text):
            footnotes.append(normalized)
        else:
            # This is body text (inside article, not a footnote)
            body.append(normalized)

    return body, footnotes


def extract_michigan_law_review_positive(soup: BeautifulSoup) -> tuple[list[str], list[str]]:
    """
    Extract Michigan Law Review using PURE POSITIVE INCLUSION.

    Definitive markers:
    - Body text: <p> tags inside <div class="wrap-wysiwyg">
    - Footnotes: <span class='modern-footnotes-footnote__note'>

    NO exclusion filters - if it's in the definitive tag, include it.
    Only skip truly empty elements (whitespace only).
    """
    body = []
    footnotes = []

    # Extract body text from definitive container
    wrap_wysiwyg = soup.find("div", class_="wrap-wysiwyg")
    if wrap_wysiwyg:
        for p in wrap_wysiwyg.find_all("p", recursive=True):
            text = p.get_text(separator=" ", strip=True)
            # Skip ONLY truly empty paragraphs
            if not text or len(text) == 0:
                continue
            body.append(normalize_text(text))

    # Extract footnotes from definitive spans (pure positive inclusion)
    modern_fn = soup.find_all("span", class_="modern-footnotes-footnote__note")
    for fn in modern_fn:
        text = fn.get_text(separator=" ", strip=True)
        # Skip ONLY truly empty spans
        if not text or len(text) == 0:
            continue
        footnotes.append(normalize_text(text))

    return body, footnotes


def extract_usc_law_review_positive(soup: BeautifulSoup) -> tuple[list[str], list[str]]:
    """
    Extract USC Law Review using PURE POSITIVE INCLUSION.

    USC uses INLINE footnotes - footnote content is embedded within paragraphs.

    Definitive markers:
    - Footnotes: <span class='modern-footnotes-footnote__note'> (inline within <p>)
    - Body text: <p> tags with footnote spans REMOVED

    NO exclusion filters - if it's in the definitive tag, include it.
    Only skip truly empty elements (whitespace only).
    """
    body = []
    footnotes = []

    # Extract footnotes from inline spans (pure positive inclusion)
    modern_fn = soup.find_all("span", class_="modern-footnotes-footnote__note")
    for fn in modern_fn:
        text = fn.get_text(strip=True)
        # Skip ONLY truly empty spans
        if not text or len(text) == 0:
            continue
        footnotes.append(normalize_text(text))

    # Extract body text from <p> tags, excluding the inline footnote content
    for p in soup.find_all("p"):
        # Create a copy to avoid modifying the original soup
        p_copy = BeautifulSoup(str(p), "html.parser").find("p")

        # Remove footnote spans and superscript markers from the copy
        for fn_span in p_copy.find_all(class_="modern-footnotes-footnote__note"):
            fn_span.decompose()
        for sup in p_copy.find_all("sup", class_="modern-footnotes-footnote"):
            sup.decompose()

        # Get the remaining text (body only)
        text = p_copy.get_text(strip=True)

        # Skip ONLY truly empty paragraphs
        if not text or len(text) == 0:
            continue
        body.append(normalize_text(text))

    return body, footnotes


def extract_supreme_court_review_positive(soup: BeautifulSoup) -> tuple[list[str], list[str]]:
    """
    Extract Supreme Court Review using PURE POSITIVE INCLUSION.

    Definitive markers:
    - Body text: <p> tags inside <article> that are NOT inside NLM_fn spans
    - Footnotes: <span class='NLM_fn'>

    NO exclusion filters - if it's in the definitive tag, include it.
    Only skip truly empty elements (whitespace only).
    """
    body = []
    footnotes = []

    # Extract footnotes from definitive spans (pure positive inclusion)
    nlm_fn = soup.find_all("span", class_="NLM_fn")
    for fn in nlm_fn:
        text = fn.get_text(separator=" ", strip=True)
        # Skip ONLY truly empty spans
        if not text or len(text) == 0:
            continue
        footnotes.append(normalize_text(text))

    # Extract body text from article (excluding NLM_fn spans)
    article = soup.find("article")
    if article:
        for p in article.find_all("p"):
            # Skip if inside NLM_fn span
            if p.find_parent(class_="NLM_fn"):
                continue

            text = p.get_text(separator=" ", strip=True)
            # Skip ONLY truly empty paragraphs
            if not text or len(text) == 0:
                continue
            body.append(normalize_text(text))

    return body, footnotes


def extract_columbia_positive(soup: BeautifulSoup) -> tuple[list[str], list[str]]:
    """
    Extract Columbia Law Review using PURE POSITIVE INCLUSION.

    Definitive markers:
    - Footnotes: <span class='footnote-text'>
    - Body text: <p> tags NOT inside footnote-text spans

    NO exclusion filters - if it's in the definitive tag, include it.
    Only skip truly empty elements (whitespace only).
    """
    body = []
    footnotes = []

    # Extract footnotes from definitive spans (pure positive inclusion)
    footnote_spans = soup.find_all("span", class_="footnote-text")
    for fn in footnote_spans:
        text = fn.get_text(separator=" ", strip=True)
        # Remove footnote number prefix
        text = re.sub(r"^\d+\s*", "", text)
        # Skip ONLY truly empty after removing number
        if not text or len(text) == 0:
            continue
        footnotes.append(normalize_text(text))

    # Extract body text (excluding footnote-text spans)
    for p in soup.find_all("p"):
        if p.find_parent(class_="footnote-text"):
            continue

        text = p.get_text(separator=" ", strip=True)
        # Skip ONLY truly empty paragraphs
        if not text or len(text) == 0:
            continue
        body.append(normalize_text(text))

    return body, footnotes


def extract_chicago_positive(soup: BeautifulSoup) -> tuple[list[str], list[str]]:
    """
    Extract University of Chicago using PURE POSITIVE INCLUSION.

    Definitive markers:
    - Footnotes: <ul class='footnotes'> > <li> elements
    - Body text: <p> tags NOT inside footnotes list

    NO exclusion filters - if it's in the definitive tag, include it.
    Only skip truly empty elements (whitespace only).
    """
    body = []
    footnotes = []

    # Extract footnotes from definitive list (pure positive inclusion)
    footnote_list = soup.find("ul", class_="footnotes")
    if footnote_list:
        for li in footnote_list.find_all("li"):
            text = li.get_text(separator=" ", strip=True)
            # Skip ONLY truly empty list items
            if not text or len(text) == 0:
                continue
            footnotes.append(normalize_text(text))

    # Extract body text (excluding footnotes list)
    for p in soup.find_all("p"):
        if p.find_parent(class_="footnotes"):
            continue

        text = p.get_text(separator=" ", strip=True)
        # Skip ONLY truly empty paragraphs
        if not text or len(text) == 0:
            continue
        body.append(normalize_text(text))

    return body, footnotes


def extract_superscript_pattern_positive(soup: BeautifulSoup) -> tuple[list[str], list[str]]:
    """
    Extract journals with superscript-only pattern using PURE POSITIVE INCLUSION.

    Definitive markers:
    - Footnotes: <div/section/aside> with 'footnote'/'endnote'/'notes' in class
    - Body text: <p> tags NOT inside footnote sections

    NO exclusion filters - if it's in the definitive tag, include it.
    Only skip truly empty elements (whitespace only).
    """
    body = []
    footnotes = []

    # Find definitive footnote sections
    all_footnote_sections = soup.find_all(
        ["div", "section", "aside"],
        class_=lambda x: x
        and any(marker in str(x).lower() for marker in ["footnote", "endnote", "notes"]),
    )

    # Filter to keep only top-level sections (not nested inside other footnote sections)
    # This prevents double-counting footnotes from both parent and child containers
    footnote_sections = []
    for section in all_footnote_sections:
        # Check if this section is inside another footnote section
        is_nested = any(
            section in parent.find_all(["div", "section", "aside"]) and section != parent
            for parent in all_footnote_sections
        )
        if not is_nested:
            footnote_sections.append(section)

    # Extract footnotes from definitive sections (pure positive inclusion)
    for section in footnote_sections:
        for p in section.find_all("p"):
            text = p.get_text(separator=" ", strip=True)
            # Skip ONLY truly empty paragraphs
            if not text or len(text) == 0:
                continue
            footnotes.append(normalize_text(text))

    # Extract body text (excluding footnote sections)
    for p in soup.find_all("p"):
        # Skip if in footnote section
        in_footnote_section = any(p in section.find_all("p") for section in footnote_sections)
        if in_footnote_section:
            continue

        text = p.get_text(separator=" ", strip=True)
        # Skip ONLY truly empty paragraphs
        if not text or len(text) == 0:
            continue
        body.append(normalize_text(text))

    return body, footnotes


def extract_bracket_paragraph_format(soup: BeautifulSoup) -> tuple[list[str], list[str]]:
    """
    Extract journals using [N]. paragraph format (California, UCLA).

    Definitive markers:
    - Footnotes: <p> or <small> tags starting with [N]. pattern
      - California uses <p> tags
      - UCLA uses <small> tags
    - Body text: All other <p> tags

    NO exclusion filters - if it's in the definitive tag, include it.
    Only skip truly empty elements (whitespace only).
    """
    import re

    body = []
    footnotes = []

    # Check BOTH <p> and <small> tags for footnotes
    # California uses <p>, UCLA uses <small>
    all_p = soup.find_all("p")
    all_small = soup.find_all("small")

    # Extract footnotes from <p> tags (California)
    for p in all_p:
        text = p.get_text(strip=True)  # Don't use separator - it breaks [N]. pattern

        # Skip ONLY truly empty
        if not text or len(text) == 0:
            continue

        normalized = normalize_text(text)

        # Check if starts with [N]. pattern (footnote)
        if re.match(r"^\[\d+\]\.", text):
            footnotes.append(normalized)
        else:
            body.append(normalized)

    # Extract footnotes from <small> tags (UCLA)
    small_matches = 0
    for s in all_small:
        text = s.get_text(strip=True)  # Don't use separator - it breaks [N]. pattern

        # Skip ONLY truly empty
        if not text or len(text) == 0:
            continue

        normalized = normalize_text(text)

        # Check if starts with [N]. pattern (footnote)
        if re.match(r"^\[\d+\]\.", text):
            small_matches += 1
            # Avoid duplicates: only add if not already in footnotes
            if normalized not in footnotes:
                footnotes.append(normalized)

    return body, footnotes


def extract_ordered_list_format(soup: BeautifulSoup) -> tuple[list[str], list[str]]:
    """
    Extract journals using <ol> list format for footnotes (Texas).

    Definitive markers:
    - Footnotes: <li> items in large <ol> lists (>50 items)
    - Body text: <p> tags NOT inside the footnote list

    NO exclusion filters - if it's in the definitive tag, include it.
    Only skip truly empty elements (whitespace only).
    """
    body = []
    footnotes = []

    # Find large <ol> lists (footnotes are typically in long ordered lists)
    footnote_list = None
    all_lists = soup.find_all(["ol", "ul"])

    for lst in all_lists:
        items = lst.find_all("li", recursive=False)
        # Footnote lists are typically large (>50 items)
        if len(items) > 50:
            footnote_list = lst
            break

    # Extract footnotes from <ol> list
    if footnote_list:
        for li in footnote_list.find_all("li", recursive=False):
            text = li.get_text(separator=" ", strip=True)
            # Skip ONLY truly empty list items
            if not text or len(text) == 0:
                continue
            # Remove back arrows or other navigation symbols
            text = text.replace("↑", "").replace("↩", "").strip()
            footnotes.append(normalize_text(text))

    # Extract body text (excluding the footnote list)
    for p in soup.find_all("p"):
        # Skip if inside the footnote list
        if footnote_list and p in footnote_list.find_all("p"):
            continue

        text = p.get_text(separator=" ", strip=True)
        # Skip ONLY truly empty paragraphs
        if not text or len(text) == 0:
            continue
        body.append(normalize_text(text))

    return body, footnotes


def extract_wisconsin_law_review_positive(soup: BeautifulSoup) -> tuple[list[str], list[str]]:
    """
    Extract Wisconsin Law Review using PURE POSITIVE INCLUSION.

    Definitive markers:
    - Footnotes: <li id="note-N"> items (anywhere in document)
    - Body text: <p> tags NOT inside footnote lists

    NO exclusion filters - if it's in the definitive tag, include it.
    Only skip truly empty elements (whitespace only).
    """
    body = []
    footnotes = []

    # Find ALL <li id="note-N"> items (regardless of parent structure)
    note_items = soup.find_all("li", id=lambda x: x and "note-" in str(x))

    # Collect all parent lists containing footnotes (to exclude from body extraction)
    footnote_lists = []
    for li in note_items:
        # Find the parent <ol> or <ul>
        parent_list = li.find_parent(["ol", "ul"])
        if parent_list and parent_list not in footnote_lists:
            footnote_lists.append(parent_list)

    # Extract footnotes from all <li id="note-N"> items
    for li in note_items:
        text = li.get_text(separator=" ", strip=True)
        # Skip ONLY truly empty list items
        if not text or len(text) == 0:
            continue
        # Remove back arrows or other navigation symbols
        text = text.replace("↑", "").replace("↩", "").strip()
        footnotes.append(normalize_text(text))

    # Extract body text (excluding footnote lists)
    for p in soup.find_all("p"):
        # Skip if inside any footnote list
        in_footnote_list = any(p in fn_list.find_all("p") for fn_list in footnote_lists)
        if in_footnote_list:
            continue

        text = p.get_text(separator=" ", strip=True)
        # Skip ONLY truly empty paragraphs
        if not text or len(text) == 0:
            continue
        body.append(normalize_text(text))

    return body, footnotes


def extract_virginia_law_review_positive(soup: BeautifulSoup) -> tuple[list[str], list[str]]:
    """
    Extract Virginia Law Review using PURE POSITIVE INCLUSION.

    Virginia uses INLINE footnotes - footnote content is embedded within paragraphs.

    Definitive markers:
    - Footnotes: <span class="foot-ref"> (inline within <p>) + <li id="post-NNNN-footnote-N">
    - Body text: <p> tags with footnote spans REMOVED

    NO exclusion filters - if it's in the definitive tag, include it.
    Only skip truly empty elements (whitespace only).
    """
    import re

    body = []
    footnotes = []

    # Extract inline footnotes from <span class="foot-ref"> spans
    inline_fn_spans = soup.find_all("span", class_=re.compile(r"foot-ref"))
    for fn_span in inline_fn_spans:
        text = fn_span.get_text(strip=True)
        # Skip ONLY truly empty spans
        if not text or len(text) == 0:
            continue
        # Remove "Show More" markers and navigation symbols
        text = text.replace("Show More", "").replace("↑", "").replace("↩", "").strip()
        # Remove leading footnote numbers (e.g., "1. " or "2. ")
        text = re.sub(r"^\d+\.\s*", "", text)
        footnotes.append(normalize_text(text))

    # Find ALL <li id="post-*-footnote-N"> items (backup footnotes at end of article)
    note_items = soup.find_all("li", id=re.compile(r"post-\d+-footnote-\d+"))

    # Collect all parent lists containing footnotes (to exclude from body extraction)
    footnote_lists = []
    for li in note_items:
        # Find the parent <ol> or <ul>
        parent_list = li.find_parent(["ol", "ul"])
        if parent_list and parent_list not in footnote_lists:
            footnote_lists.append(parent_list)

    # Extract footnotes from all matching <li> items (if not already extracted from inline)
    for li in note_items:
        text = li.get_text(separator=" ", strip=True)
        # Skip ONLY truly empty list items
        if not text or len(text) == 0:
            continue
        # Remove back arrows or other navigation symbols
        text = text.replace("↑", "").replace("↩", "").strip()
        # Remove leading footnote numbers
        text = re.sub(r"^\d+\.\s*", "", text)
        footnotes.append(normalize_text(text))

    # Extract body text from <p> tags, excluding the inline footnote content
    for p in soup.find_all("p"):
        # Skip if inside any footnote list
        in_footnote_list = any(p in fn_list.find_all("p") for fn_list in footnote_lists)
        if in_footnote_list:
            continue

        # Create a copy to avoid modifying the original soup
        p_copy = BeautifulSoup(str(p), "html.parser").find("p")

        # Remove footnote spans and superscript markers from the copy
        for fn_span in p_copy.find_all("span", class_=re.compile(r"foot-ref")):
            fn_span.decompose()
        for sup in p_copy.find_all("sup", class_="footnote"):
            sup.decompose()

        # Get the remaining text (body only)
        text = p_copy.get_text(strip=True)

        # Skip ONLY truly empty paragraphs
        if not text or len(text) == 0:
            continue
        body.append(normalize_text(text))

    return body, footnotes


def extract_labeled_paragraphs(html_path: Path) -> tuple[list[dict], str]:
    """
    Extract paragraphs using POSITIVE INCLUSION strategy.

    Returns:
        Tuple of (paragraphs list, journal name)
    """
    try:
        with open(html_path, encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "html.parser")
    except Exception as e:
        print(f"  ⚠️  Error reading HTML: {e}")
        return [], "Unknown"

    # Identify journal BEFORE removing scripts (uses title/meta tags)
    journal = identify_journal(html_path.name, soup)

    # Remove script and style tags
    for script in soup(["script", "style"]):
        script.decompose()

    if journal == "BU Law Review":
        body_texts, footnote_texts = extract_bu_law_review_positive(soup)
    elif journal == "Michigan Law Review":
        body_texts, footnote_texts = extract_michigan_law_review_positive(soup)
    elif journal == "USC Law Review":
        body_texts, footnote_texts = extract_usc_law_review_positive(soup)
    elif journal == "Supreme Court Review":
        body_texts, footnote_texts = extract_supreme_court_review_positive(soup)
    elif journal == "Columbia Law Review":
        body_texts, footnote_texts = extract_columbia_positive(soup)
    elif journal == "University of Chicago Law Review":
        body_texts, footnote_texts = extract_chicago_positive(soup)
    elif journal in ["California Law Review", "UCLA Law Review"]:
        # [N]. paragraph format
        body_texts, footnote_texts = extract_bracket_paragraph_format(soup)
    elif journal == "Texas Law Review":
        # <ol> list format
        body_texts, footnote_texts = extract_ordered_list_format(soup)
    elif journal == "Wisconsin Law Review":
        # <li id="note-N"> format following <h2>Footnotes</h2>
        body_texts, footnote_texts = extract_wisconsin_law_review_positive(soup)
    elif journal == "Virginia Law Review":
        # <li id="post-*-footnote-N"> format in <ol class="foot_notes">
        body_texts, footnote_texts = extract_virginia_law_review_positive(soup)
    elif journal in ["Harvard Law Review", "Penn Law Review"]:
        # Superscript pattern
        body_texts, footnote_texts = extract_superscript_pattern_positive(soup)
    else:
        # Fallback: generic extraction
        print(f"    ℹ️  Using generic extraction for unknown journal: {journal}")
        body_texts, footnote_texts = extract_superscript_pattern_positive(soup)

    # Create labeled paragraph list (PURE POSITIVE INCLUSION - no filters)
    paragraphs = []

    # Add body text - include ALL extracted paragraphs
    for text in body_texts:
        word_count = len(text.split())
        paragraphs.append(
            {
                "text": text,
                "label": "body-text",
                "word_count": word_count,
            }
        )

    # Add footnotes - include ALL extracted footnotes
    for text in footnote_texts:
        word_count = len(text.split())
        paragraphs.append(
            {
                "text": text,
                "label": "footnote-text",
                "word_count": word_count,
            }
        )

    return paragraphs, journal


def save_labeled_html(basename: str, paragraphs: list[dict], journal: str):
    """Save labeled paragraph structure to JSON."""
    LABELED_HTML_DIR.mkdir(parents=True, exist_ok=True)
    output_file = LABELED_HTML_DIR / f"{basename}.json"

    # Calculate stats
    body_count = sum(1 for p in paragraphs if p["label"] == "body-text")
    footnote_count = sum(1 for p in paragraphs if p["label"] == "footnote-text")
    total_words = sum(p["word_count"] for p in paragraphs)

    data = {
        "basename": basename,
        "journal": journal,
        "extraction_method": "positive_inclusion",
        "stats": {
            "total_paragraphs": len(paragraphs),
            "body_text": body_count,
            "footnote_text": footnote_count,
            "total_words": total_words,
        },
        "paragraphs": paragraphs,
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return output_file


def process_corpus():
    """Process all HTML files using positive inclusion strategy."""
    html_dir = Path("data/v3_data/raw_html")

    if not html_dir.exists():
        print("❌ HTML directory not found: data/v3_data/raw_html/")
        return

    html_files = sorted(html_dir.glob("*.html"))

    print("📝 Extracting labeled paragraphs using POSITIVE INCLUSION strategy")
    print(f"Found {len(html_files)} HTML files")
    print(f"Output directory: {LABELED_HTML_DIR}\n")
    print("=" * 80)

    results = []

    for html_file in html_files:
        basename = html_file.stem
        print(f"\n{basename}")
        print("-" * 80)

        # Extract labeled paragraphs
        paragraphs, journal = extract_labeled_paragraphs(html_file)

        if not paragraphs:
            print("    ❌ No paragraphs extracted")
            continue

        # Save to JSON
        output_file = save_labeled_html(basename, paragraphs, journal)

        # Report stats
        body_count = sum(1 for p in paragraphs if p["label"] == "body-text")
        footnote_count = sum(1 for p in paragraphs if p["label"] == "footnote-text")
        total_words = sum(p["word_count"] for p in paragraphs)

        print(f"  Journal: {journal}")
        print(f"  ✅ Extracted {len(paragraphs)} paragraphs:")
        print(f"     Body text:     {body_count:>4} paragraphs")
        print(f"     Footnote text: {footnote_count:>4} paragraphs")
        print(f"     Total words:   {total_words:,}")
        print(f"  💾 Saved to: {output_file}")

        results.append(
            {
                "basename": basename,
                "journal": journal,
                "paragraphs": len(paragraphs),
                "body": body_count,
                "footnotes": footnote_count,
                "words": total_words,
            }
        )

    # Summary by journal
    print(f"\n\n{'=' * 80}")
    print("EXTRACTION SUMMARY BY JOURNAL")
    print(f"{'=' * 80}\n")

    by_journal = {}
    for r in results:
        journal = r["journal"]
        if journal not in by_journal:
            by_journal[journal] = {"count": 0, "body": 0, "footnotes": 0}
        by_journal[journal]["count"] += 1
        by_journal[journal]["body"] += r["body"]
        by_journal[journal]["footnotes"] += r["footnotes"]

    for journal in sorted(by_journal.keys()):
        stats = by_journal[journal]
        print(f"{journal:40}")
        print(f"  Articles:  {stats['count']:>4}")
        print(f"  Body text: {stats['body']:>4} paragraphs")
        print(f"  Footnotes: {stats['footnotes']:>4} paragraphs")
        print()

    total_articles = len(results)
    total_body = sum(r["body"] for r in results)
    total_footnotes = sum(r["footnotes"] for r in results)

    print(f"{'=' * 80}")
    print(
        f"TOTAL: {total_articles} articles, {total_body} body paragraphs, {total_footnotes} footnotes"
    )


if __name__ == "__main__":
    process_corpus()
