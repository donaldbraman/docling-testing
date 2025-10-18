#!/usr/bin/env python3
"""Extract article-only content from HTML and label paragraphs as body-text or footnote-text."""

import json
import re
from pathlib import Path

from bs4 import BeautifulSoup

LABELED_HTML_DIR = Path("data/labeled_html")


def normalize_text(text: str) -> str:
    """Normalize text for consistency."""
    text = text.lower()
    text = re.sub(r"\s+", " ", text)  # Collapse whitespace
    text = re.sub(r"-\s+", "", text)  # Remove line-break hyphens
    text = re.sub(r'["' '"]', '"', text)  # Normalize quotes
    text = re.sub(r"[–—]", "-", text)  # Normalize dashes
    return text.strip()


def find_article_container(soup: BeautifulSoup):
    """Find the main article container in HTML."""
    # Try various common article container patterns
    containers = [
        soup.find("article"),
        soup.find(
            class_=re.compile(r"(entry-content|article-content|post-content|main-content)", re.I)
        ),
        soup.find("main"),
        soup.find(id=re.compile(r"(content|article|main)", re.I)),
    ]

    for container in containers:
        if container:
            return container

    # Fallback: use body but warn
    print("    ⚠️  No article container found, using <body>")
    return soup.find("body")


def is_footnote_element(element) -> bool:
    """Check if an element is a footnote based on HTML structure."""
    # Check class names
    if element.get("class"):
        classes = " ".join(element["class"]).lower()
        if any(marker in classes for marker in ["footnote", "endnote", "fn", "note"]):
            return True

    # Check if inside footnote section
    parent = element.parent
    while parent:
        if parent.name in ["footer", "aside"]:
            return True
        if parent.get("class"):
            parent_classes = " ".join(parent["class"]).lower()
            if any(marker in parent_classes for marker in ["footnote", "endnote", "notes"]):
                return True
        parent = parent.parent

    return False


def extract_labeled_paragraphs(html_path: Path) -> list[dict]:
    """
    Extract paragraphs from HTML article content and label them.

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

    # Find article container
    article = find_article_container(soup)
    if not article:
        print("    ⚠️  No article content found")
        return []

    # Extract paragraphs
    paragraphs = []
    for p in article.find_all("p"):
        text = p.get_text(separator=" ", strip=True)

        # Skip empty or very short paragraphs
        if len(text) < 20:
            continue

        # Normalize text
        normalized = normalize_text(text)
        word_count = len(normalized.split())

        # Skip if mostly non-text (numbers, punctuation)
        text_only = re.sub(r"[^a-zA-Z]", "", normalized)
        if len(text_only) < len(normalized) * 0.5:
            continue

        # Label as footnote or body text
        label = "footnote-text" if is_footnote_element(p) else "body-text"

        paragraphs.append(
            {
                "text": normalized,
                "label": label,
                "word_count": word_count,
            }
        )

    return paragraphs


def save_labeled_html(basename: str, paragraphs: list[dict]):
    """Save labeled paragraph structure to JSON."""
    LABELED_HTML_DIR.mkdir(parents=True, exist_ok=True)
    output_file = LABELED_HTML_DIR / f"{basename}.json"

    # Calculate stats
    body_count = sum(1 for p in paragraphs if p["label"] == "body-text")
    footnote_count = sum(1 for p in paragraphs if p["label"] == "footnote-text")
    total_words = sum(p["word_count"] for p in paragraphs)

    data = {
        "basename": basename,
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

    print("📝 Extracting labeled paragraphs from HTML corpus")
    print(f"Found {len(html_files)} HTML files")
    print(f"Output directory: {LABELED_HTML_DIR}\n")
    print("=" * 70)

    results = []

    for html_file in html_files:
        basename = html_file.stem
        print(f"\n{basename}")
        print("-" * 70)

        # Extract labeled paragraphs
        print("  Extracting article content...")
        paragraphs = extract_labeled_paragraphs(html_file)

        if not paragraphs:
            print("    ❌ No paragraphs extracted")
            continue

        # Save to JSON
        output_file = save_labeled_html(basename, paragraphs)

        # Report stats
        body_count = sum(1 for p in paragraphs if p["label"] == "body-text")
        footnote_count = sum(1 for p in paragraphs if p["label"] == "footnote-text")
        total_words = sum(p["word_count"] for p in paragraphs)

        print(f"  ✅ Extracted {len(paragraphs)} paragraphs:")
        print(f"     Body text:     {body_count} paragraphs")
        print(f"     Footnote text: {footnote_count} paragraphs")
        print(f"     Total words:   {total_words:,}")
        print(f"  💾 Saved to: {output_file}")

        results.append(
            {
                "basename": basename,
                "paragraphs": len(paragraphs),
                "body": body_count,
                "footnotes": footnote_count,
                "words": total_words,
            }
        )

    # Summary
    print(f"\n\n{'=' * 70}")
    print("CORPUS EXTRACTION SUMMARY")
    print(f"{'=' * 70}\n")

    if results:
        total_files = len(results)
        total_paras = sum(r["paragraphs"] for r in results)
        total_body = sum(r["body"] for r in results)
        total_footnotes = sum(r["footnotes"] for r in results)
        total_words = sum(r["words"] for r in results)

        print(f"Files processed:       {total_files}")
        print(f"Total paragraphs:      {total_paras:,}")
        print(f"  Body text:           {total_body:,} ({total_body / total_paras * 100:.1f}%)")
        print(
            f"  Footnote text:       {total_footnotes:,} ({total_footnotes / total_paras * 100:.1f}%)"
        )
        print(f"Total words:           {total_words:,}")
        print("\nAverage per document:")
        print(f"  Paragraphs:          {total_paras / total_files:.0f}")
        print(f"  Words:               {total_words / total_files:,.0f}")

        print(f"\n📁 Labeled HTML files: {LABELED_HTML_DIR}/")
    else:
        print("❌ No files processed successfully")

    print(f"{'=' * 70}\n")


if __name__ == "__main__":
    process_corpus()
