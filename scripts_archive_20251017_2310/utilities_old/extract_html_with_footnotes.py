#!/usr/bin/env python3
"""
Extract complete HTML content including ALL footnotes.

This script extracts both body text and footnotes from HTML files,
using journal-specific patterns to ensure complete footnote capture.
"""

import json
import re
from pathlib import Path

from bs4 import BeautifulSoup

LABELED_HTML_DIR = Path("data/labeled_html_v2")  # New output directory to preserve old data


def normalize_text(text: str) -> str:
    """Normalize text for consistency."""
    text = re.sub(r"\s+", " ", text)  # Collapse whitespace
    text = re.sub(r"-\s+", "", text)  # Remove line-break hyphens
    return text.strip()


def identify_journal(filename: str) -> str:
    """Identify journal from filename."""
    lower = filename.lower()
    if "bu_law_review" in lower or "bu law review" in lower:
        return "BU Law Review"
    elif "columbia" in lower and "law review" in lower:
        return "Columbia Law Review"
    elif "michigan_law_review" in lower:
        return "Michigan Law Review"
    elif "usc_law_review" in lower:
        return "USC Law Review"
    elif "supreme_court_review" in lower:
        return "Supreme Court Review"
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
    else:
        return "Unknown"


def extract_bu_law_review(soup: BeautifulSoup) -> tuple[list[str], list[str]]:
    """Extract body text and footnotes for BU Law Review (bracket pattern)."""
    body = []
    footnotes = []

    # Find all paragraphs
    for p in soup.find_all("p"):
        text = p.get_text(separator=" ", strip=True)
        if len(text) < 20:
            continue

        normalized = normalize_text(text)

        # Check if starts with [N] pattern (footnote)
        if re.match(r"^\[\d+\]", text):
            footnotes.append(normalized)
        else:
            # Skip navigation/header paragraphs (use more specific patterns)
            lower_text = text.lower()
            if any(
                skip in lower_text
                for skip in ["skip to content", "main menu", "search this site", "home page"]
            ):
                continue
            body.append(normalized)

    return body, footnotes


def extract_michigan_usc(soup: BeautifulSoup) -> tuple[list[str], list[str]]:
    """Extract body text and footnotes for Michigan/USC (modern-footnotes plugin)."""
    body = []
    footnotes = []

    # Extract footnotes from modern-footnotes plugin
    modern_fn = soup.find_all("span", class_="modern-footnotes-footnote__note")
    for fn in modern_fn:
        text = fn.get_text(separator=" ", strip=True)
        if len(text) >= 20:
            footnotes.append(normalize_text(text))

    # Extract body text from paragraphs (excluding those inside footnotes)
    for p in soup.find_all("p"):
        # Skip if inside modern-footnotes container
        if p.find_parent(class_=lambda x: x and "modern-footnotes" in " ".join(x).lower()):
            continue

        text = p.get_text(separator=" ", strip=True)
        if len(text) >= 20:
            lower_text = text.lower()
            if not any(
                skip in lower_text
                for skip in ["skip to content", "main menu", "search this site", "home page"]
            ):
                body.append(normalize_text(text))

    return body, footnotes


def extract_supreme_court(soup: BeautifulSoup) -> tuple[list[str], list[str]]:
    """Extract body text and footnotes for Supreme Court Review (NLM_fn pattern)."""
    body = []
    footnotes = []

    # Extract footnotes from NLM_fn spans
    nlm_fn = soup.find_all("span", class_="NLM_fn")
    for fn in nlm_fn:
        text = fn.get_text(separator=" ", strip=True)
        if len(text) >= 20:
            footnotes.append(normalize_text(text))

    # Extract body text
    for p in soup.find_all("p"):
        # Skip if inside NLM_fn
        if p.find_parent(class_="NLM_fn"):
            continue

        text = p.get_text(separator=" ", strip=True)
        if len(text) >= 20:
            lower_text = text.lower()
            if not any(
                skip in lower_text
                for skip in ["skip to content", "main menu", "search this site", "home page"]
            ):
                body.append(normalize_text(text))

    return body, footnotes


def extract_columbia(soup: BeautifulSoup) -> tuple[list[str], list[str]]:
    """Extract body text and footnotes for Columbia Law Review (inline JS pattern)."""
    body = []
    footnotes = []

    # Extract footnotes from inline JS system
    footnote_spans = soup.find_all("span", class_="footnote-text")
    for fn in footnote_spans:
        text = fn.get_text(separator=" ", strip=True)
        # Remove footnote number prefix
        text = re.sub(r"^\d+\s*", "", text)
        if len(text) >= 20:
            footnotes.append(normalize_text(text))

    # Extract body text
    for p in soup.find_all("p"):
        # Skip if inside footnote-text
        if p.find_parent(class_="footnote-text"):
            continue

        text = p.get_text(separator=" ", strip=True)
        if len(text) >= 20:
            lower_text = text.lower()
            if not any(
                skip in lower_text
                for skip in ["skip to content", "main menu", "search this site", "home page"]
            ):
                body.append(normalize_text(text))

    return body, footnotes


def extract_chicago(soup: BeautifulSoup) -> tuple[list[str], list[str]]:
    """Extract body text and footnotes for University of Chicago (see-footnote pattern)."""
    body = []
    footnotes = []

    # Extract footnotes from <ul class="footnotes">
    footnote_list = soup.find("ul", class_="footnotes")
    if footnote_list:
        for li in footnote_list.find_all("li"):
            text = li.get_text(separator=" ", strip=True)
            if len(text) >= 20:
                footnotes.append(normalize_text(text))

    # Extract body text
    for p in soup.find_all("p"):
        # Skip if inside footnotes list
        if p.find_parent(class_="footnotes"):
            continue

        text = p.get_text(separator=" ", strip=True)
        if len(text) >= 20:
            lower_text = text.lower()
            if not any(
                skip in lower_text
                for skip in ["skip to content", "main menu", "search this site", "home page"]
            ):
                body.append(normalize_text(text))

    return body, footnotes


def extract_superscript_pattern(soup: BeautifulSoup) -> tuple[list[str], list[str]]:
    """Extract for journals with superscript-only pattern (Harvard, Texas, Virginia, Wisconsin, Penn)."""
    body = []
    footnotes = []

    # Look for footnote section at end
    # Common patterns: sections/divs with 'footnote', 'endnote', 'notes' in class or id
    footnote_sections = soup.find_all(
        ["div", "section", "aside"],
        class_=lambda x: x
        and any(marker in " ".join(x).lower() for marker in ["footnote", "endnote", "notes"]),
    )

    for section in footnote_sections:
        for p in section.find_all("p"):
            text = p.get_text(separator=" ", strip=True)
            if len(text) >= 20:
                footnotes.append(normalize_text(text))

    # Extract body text (excluding footnote sections)
    for p in soup.find_all("p"):
        # Skip if in footnote section
        in_footnote_section = False
        for section in footnote_sections:
            if p.find_parent() and p in section.find_all("p"):
                in_footnote_section = True
                break

        if in_footnote_section:
            continue

        text = p.get_text(separator=" ", strip=True)
        if len(text) >= 20:
            lower_text = text.lower()
            if not any(
                skip in lower_text
                for skip in ["skip to content", "main menu", "search this site", "home page"]
            ):
                body.append(normalize_text(text))

    return body, footnotes


def extract_labeled_paragraphs(html_path: Path) -> list[dict]:
    """
    Extract ALL paragraphs from HTML including footnotes.

    Returns:
        List of dicts with keys: text, label, word_count
    """
    try:
        with open(html_path, encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "html.parser")
    except Exception as e:
        print(f"  ⚠️  Error reading HTML: {e}")
        return []

    # Remove script and style tags
    for script in soup(["script", "style"]):
        script.decompose()

    # Identify journal and use appropriate extraction method
    journal = identify_journal(html_path.name)

    if journal == "BU Law Review":
        body_texts, footnote_texts = extract_bu_law_review(soup)
    elif journal in ["Michigan Law Review", "USC Law Review"]:
        body_texts, footnote_texts = extract_michigan_usc(soup)
    elif journal == "Supreme Court Review":
        body_texts, footnote_texts = extract_supreme_court(soup)
    elif journal == "Columbia Law Review":
        body_texts, footnote_texts = extract_columbia(soup)
    elif journal == "University of Chicago Law Review":
        body_texts, footnote_texts = extract_chicago(soup)
    elif journal in [
        "Harvard Law Review",
        "Texas Law Review",
        "Virginia Law Review",
        "Wisconsin Law Review",
        "Penn Law Review",
        "California Law Review",
    ]:
        body_texts, footnote_texts = extract_superscript_pattern(soup)
    else:
        # Fallback: generic extraction
        print(f"    ℹ️  Using generic extraction for unknown journal: {journal}")
        body_texts, footnote_texts = extract_superscript_pattern(soup)

    # Create labeled paragraph list
    paragraphs = []

    # Add body text
    for text in body_texts:
        word_count = len(text.split())
        if word_count >= 5:  # At least 5 words
            paragraphs.append(
                {
                    "text": text,
                    "label": "body-text",
                    "word_count": word_count,
                }
            )

    # Add footnotes
    for text in footnote_texts:
        word_count = len(text.split())
        if word_count >= 5:  # At least 5 words
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
    """Process all HTML files in corpus and extract labeled paragraphs."""
    html_dir = Path("data/raw_html")

    if not html_dir.exists():
        print("❌ HTML directory not found: data/raw_html/")
        return

    html_files = sorted(html_dir.glob("*.html"))

    print("📝 Extracting complete labeled paragraphs (with footnotes) from HTML corpus")
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
