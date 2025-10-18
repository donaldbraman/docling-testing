#!/usr/bin/env python3
"""Analyze HTML structure to find definitive markers for body text and footnotes."""

from pathlib import Path

from bs4 import BeautifulSoup


def analyze_html_structure(html_path: Path) -> dict:
    """Analyze HTML structure to identify body text and footnote markers."""

    with open(html_path, encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    # Remove script and style
    for script in soup(["script", "style"]):
        script.decompose()

    analysis = {
        "file": html_path.name,
        "body_text_markers": [],
        "footnote_markers": [],
        "paragraph_tags": [],
        "div_classes": [],
        "section_classes": [],
    }

    # Find all paragraphs and their containers
    paragraphs = soup.find_all("p")
    print(f"\n{'=' * 80}")
    print(f"FILE: {html_path.name}")
    print(f"{'=' * 80}")
    print(f"Total <p> tags: {len(paragraphs)}\n")

    # Analyze paragraph patterns
    print("PARAGRAPH PATTERNS:")
    print("-" * 80)

    for i, p in enumerate(paragraphs[:10]):  # First 10 paragraphs
        text = p.get_text(strip=True)
        if len(text) < 20:
            continue

        # Get parent info
        parent = p.parent
        parent_tag = parent.name if parent else "None"
        parent_class = " ".join(parent.get("class", [])) if parent else ""
        parent_id = parent.get("id", "") if parent else ""

        # Get paragraph class/id
        p_class = " ".join(p.get("class", []))
        p_id = p.get("id", "")

        # Check for footnote indicators
        is_footnote = False
        footnote_hints = []

        # Check for [N] pattern
        if text.startswith("[") and text[1:2].isdigit():
            is_footnote = True
            footnote_hints.append("[N] pattern")

        # Check for footnote classes
        if "footnote" in p_class.lower():
            is_footnote = True
            footnote_hints.append(f"class={p_class}")
        if "footnote" in parent_class.lower():
            is_footnote = True
            footnote_hints.append(f"parent_class={parent_class}")

        # Check for modern-footnotes
        if "modern-footnotes" in str(p.get("class", "")).lower():
            is_footnote = True
            footnote_hints.append("modern-footnotes")

        # Check for NLM_fn
        if p.find("span", class_="NLM_fn"):
            is_footnote = True
            footnote_hints.append("NLM_fn span")

        label = "FOOTNOTE" if is_footnote else "BODY"

        print(f"\n[{i + 1}] {label}")
        if parent_tag != "body":
            print(f"  Parent: <{parent_tag}>")
            if parent_class:
                print(f"  Parent class: {parent_class}")
            if parent_id:
                print(f"  Parent id: {parent_id}")
        if p_class:
            print(f"  <p> class: {p_class}")
        if p_id:
            print(f"  <p> id: {p_id}")
        if footnote_hints:
            print(f"  Footnote hints: {', '.join(footnote_hints)}")
        print(f"  Text: {text[:100]}...")

    # Find all footnote-related elements
    print(f"\n\n{'=' * 80}")
    print("FOOTNOTE-SPECIFIC STRUCTURES:")
    print(f"{'=' * 80}\n")

    # Check for modern-footnotes
    modern_fn = soup.find_all("span", class_="modern-footnotes-footnote__note")
    if modern_fn:
        print(f"✓ Modern-footnotes plugin: {len(modern_fn)} footnotes")
        print(f"  Example: {modern_fn[0].get_text(strip=True)[:80]}...")

    # Check for NLM_fn
    nlm_fn = soup.find_all("span", class_="NLM_fn")
    if nlm_fn:
        print(f"✓ NLM_fn spans: {len(nlm_fn)} footnotes")
        print(f"  Example: {nlm_fn[0].get_text(strip=True)[:80]}...")

    # Check for footnote-text spans
    footnote_text = soup.find_all("span", class_="footnote-text")
    if footnote_text:
        print(f"✓ Footnote-text spans: {len(footnote_text)} footnotes")
        print(f"  Example: {footnote_text[0].get_text(strip=True)[:80]}...")

    # Check for footnotes list
    footnotes_ul = soup.find("ul", class_="footnotes")
    if footnotes_ul:
        fn_items = footnotes_ul.find_all("li")
        print(f"✓ <ul class='footnotes'>: {len(fn_items)} footnotes")
        if fn_items:
            print(f"  Example: {fn_items[0].get_text(strip=True)[:80]}...")

    # Check for [N] pattern in paragraphs
    bracket_fn = [
        p
        for p in soup.find_all("p")
        if p.get_text(strip=True).startswith("[")
        and len(p.get_text(strip=True)) > 20
        and p.get_text(strip=True)[1:2].isdigit()
    ]
    if bracket_fn:
        print(f"✓ [N] pattern paragraphs: {len(bracket_fn)} footnotes")
        print(f"  Example: {bracket_fn[0].get_text(strip=True)[:80]}...")

    # Find article content container
    print(f"\n\n{'=' * 80}")
    print("ARTICLE CONTENT CONTAINERS:")
    print(f"{'=' * 80}\n")

    # Look for main content divs
    article_tag = soup.find("article")
    if article_tag:
        print("✓ <article> tag found")
        article_classes = " ".join(article_tag.get("class", []))
        if article_classes:
            print(f"  Classes: {article_classes}")

    # Look for main content div
    main_content = soup.find(
        "div", class_=lambda x: x and ("content" in str(x).lower() or "article" in str(x).lower())
    )
    if main_content:
        main_classes = " ".join(main_content.get("class", []))
        print(f"✓ Main content div: class='{main_classes}'")

    # Look for entry-content (common in WordPress)
    entry_content = soup.find("div", class_="entry-content")
    if entry_content:
        print("✓ <div class='entry-content'> found")

    return analysis


def main():
    """Analyze HTML structure for all articles."""
    import sys

    # Get journal from command line or default to BU
    journal = sys.argv[1] if len(sys.argv) > 1 else "bu"

    journal_files = {
        "bu": "data/raw_html/bu_law_review_online_fourth_amendment_secure.html",
        "michigan": "data/raw_html/michigan_law_review_law_enforcement_privilege.html",
        "supreme": "data/raw_html/supreme_court_review_fear_of_balancing.html",
    }

    html_file = Path(journal_files.get(journal, journal_files["bu"]))

    if html_file.exists():
        analyze_html_structure(html_file)
    else:
        print(f"⚠️  File not found: {html_file}")
        print(f"\nUsage: python {sys.argv[0]} [bu|michigan|supreme]")


if __name__ == "__main__":
    main()
