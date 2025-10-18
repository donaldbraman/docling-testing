#!/usr/bin/env python3
"""Carefully investigate HTML structure to find footnote patterns."""

from pathlib import Path

from bs4 import BeautifulSoup


def investigate_html_structure(html_path: Path):
    """Carefully examine HTML structure for one article."""
    print(f"\n{'=' * 80}")
    print(f"INVESTIGATING: {html_path.stem}")
    print(f"{'=' * 80}\n")

    with open(html_path, encoding="utf-8") as f:
        html_content = f.read()

    soup = BeautifulSoup(html_content, "html.parser")

    # 1. Look at overall structure
    print("1. TOP-LEVEL STRUCTURE")
    print("-" * 80)
    body = soup.find("body")
    if body:
        children = [child.name for child in body.children if child.name]
        print(f"Body children: {children[:20]}")
        print(f"Total body children: {len([c for c in body.children if c.name])}")
    print()

    # 2. Look for sections/divs with distinctive classes or IDs
    print("2. SECTIONS AND DIVS")
    print("-" * 80)
    sections = soup.find_all(["section", "div", "article"])
    section_info = {}
    for section in sections:
        classes = " ".join(section.get("class", []))
        id_attr = section.get("id", "")
        key = f"{section.name}"
        if classes:
            key += f" class='{classes}'"
        if id_attr:
            key += f" id='{id_attr}'"

        section_info[key] = section_info.get(key, 0) + 1

    for key, count in sorted(section_info.items(), key=lambda x: -x[1])[:15]:
        print(f"  [{count:>3}x] {key}")
    print()

    # 3. Look for paragraphs with different classes
    print("3. PARAGRAPH PATTERNS")
    print("-" * 80)
    paragraphs = soup.find_all("p")
    print(f"Total paragraphs: {len(paragraphs)}\n")

    para_classes = {}
    for p in paragraphs:
        classes = " ".join(p.get("class", []))
        if not classes:
            classes = "(no class)"
        para_classes[classes] = para_classes.get(classes, 0) + 1

    for cls, count in sorted(para_classes.items(), key=lambda x: -x[1])[:10]:
        print(f"  [{count:>3}x] <p class='{cls}'>")
    print()

    # 4. Look for footnote-specific markers
    print("4. FOOTNOTE MARKERS")
    print("-" * 80)

    # Look for common footnote patterns
    footnote_patterns = [
        (
            'class containing "footnote"',
            soup.find_all(class_=lambda x: x and "footnote" in x.lower()),
        ),
        (
            'class containing "note"',
            soup.find_all(
                class_=lambda x: x and "note" in x.lower() and "footnote" not in x.lower()
            ),
        ),
        ('id containing "footnote"', soup.find_all(id=lambda x: x and "footnote" in x.lower())),
        (
            'id containing "fn"',
            soup.find_all(id=lambda x: x and "fn" in x.lower() and "footnote" not in x.lower()),
        ),
        ("<aside> tags", soup.find_all("aside")),
        ("<footer> tags", soup.find_all("footer")),
    ]

    for pattern_name, elements in footnote_patterns:
        if elements:
            print(f"  ✓ Found {len(elements):>3} elements with {pattern_name}")
            # Show first example
            if elements:
                first = elements[0]
                print(f"    Example: <{first.name}", end="")
                if first.get("class"):
                    print(f" class='{' '.join(first.get('class'))}'", end="")
                if first.get("id"):
                    print(f" id='{first.get('id')}'", end="")
                print(">")
                # Show text snippet
                text = first.get_text(strip=True)[:100]
                print(f"    Text: {text}...")
        else:
            print(f"  ✗ No elements with {pattern_name}")
    print()

    # 5. Look for specific text patterns that indicate footnotes
    print("5. FOOTNOTE TEXT PATTERNS")
    print("-" * 80)

    # Find paragraphs that start with numbers in brackets
    bracket_pattern_paras = []
    for p in paragraphs:
        text = p.get_text(strip=True)
        if text and text[0] == "[" and len(text) > 2 and text[1].isdigit():
            bracket_pattern_paras.append(p)

    print(f"  Paragraphs starting with '[N]': {len(bracket_pattern_paras)}")
    if bracket_pattern_paras:
        for i, p in enumerate(bracket_pattern_paras[:3]):
            classes = " ".join(p.get("class", []))
            parent = p.parent.name if p.parent else "None"
            parent_classes = (
                " ".join(p.parent.get("class", [])) if p.parent and hasattr(p.parent, "get") else ""
            )

            print(f"\n    Example {i + 1}:")
            print(f"      <p class='{classes}'>")
            print(f"      Parent: <{parent} class='{parent_classes}'>")
            print(f"      Text: {p.get_text(strip=True)[:150]}...")
    print()

    # 6. Look at document end structure
    print("6. END OF DOCUMENT STRUCTURE")
    print("-" * 80)
    all_paras = soup.find_all("p")
    if len(all_paras) > 10:
        print("Last 10 paragraphs:")
        for i, p in enumerate(all_paras[-10:], start=len(all_paras) - 9):
            classes = " ".join(p.get("class", []))
            parent = p.parent.name if p.parent else "None"
            text = p.get_text(strip=True)[:80]
            print(f"  [{i:>3}] <p class='{classes}'> parent={parent}")
            print(f"       {text}...")
    print()


def main():
    """Investigate HTML structure for representative files."""
    html_dir = Path("data/raw_html")

    # One from each journal
    test_files = [
        "bu_law_review_online_fourth_amendment_secure.html",
        "michigan_law_review_spending_clause_standing.html",
        "supreme_court_review_fear_of_balancing.html",
    ]

    for filename in test_files:
        html_path = html_dir / filename
        if html_path.exists():
            investigate_html_structure(html_path)


if __name__ == "__main__":
    main()
