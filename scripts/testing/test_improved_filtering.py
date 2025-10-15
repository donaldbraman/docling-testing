#!/usr/bin/env python3
"""Test improved citation filtering that checks ALL labels, not just list_item."""

import re
from pathlib import Path


def is_citation_paragraph(text: str) -> bool:
    """
    Expanded heuristic to catch footnote citations that appear as text/paragraph items.

    These are typically:
    - Standalone case citations: "554 U.S. 570 (2008)."
    - Citation signals: "See id. at 2551-52..."
    - Cross-references: "See supra note 116..."
    """
    text = text.strip()

    # Very short standalone case citations (just reporter + year)
    # Example: "554 U.S. 570 (2008)."
    if len(text) < 60 and re.match(r"^\d+\s+[A-Z]", text) and re.search(r"\(\d{4}\)", text):
        return True

    # Items starting with citation signals
    # Example: "See id. at...", "Id. at...", "See supra note..."
    if len(text) < 200 and re.match(
        r"^(See|Id\.|Ibid\.|Compare|But see|Cf\.)", text, re.IGNORECASE
    ):
        return True

    # Items that are mostly just "Id." with location
    # Example: "Id. at 682, 690 (Breyer, J., dissenting)."
    if len(text) < 150 and re.match(r"^Id\.", text):
        return True

    # Very short items ending with case citation pattern
    # Example: "532 U.S. 318 (2001)."
    if len(text) < 80 and re.search(r"\d+\s+U\.S\.\s+\d+\s+\(\d{4}\)", text):
        return True

    # Items with "supra note" or "infra note" (cross-references to footnotes)
    if len(text) < 150 and re.search(r"(supra|infra) note", text):
        return True

    return False


def analyze_body_text():
    """Analyze the current body text to see how many citations got through."""

    body_path = Path("results/body_extraction/Jackson_2014_default_body_only.txt")

    if not body_path.exists():
        print(f"❌ Body text file not found: {body_path}")
        return

    content = body_path.read_text(encoding="utf-8")
    paragraphs = content.split("\n\n")

    print(f"\n{'=' * 80}")
    print("ANALYZING CURRENT BODY TEXT FOR CITATION PATTERNS")
    print(f"{'=' * 80}\n")

    print(f"Total paragraphs: {len(paragraphs)}")

    # Check each paragraph against citation patterns
    citation_matches = []
    for para in paragraphs:
        para = para.strip()
        if para and is_citation_paragraph(para):
            citation_matches.append(para[:150])

    print(f"Citation-like paragraphs found: {len(citation_matches)}")

    print(f"\n{'=' * 80}")
    print("SAMPLE CITATION PARAGRAPHS IN BODY TEXT")
    print(f"{'=' * 80}\n")

    for i, citation in enumerate(citation_matches[:25], 1):
        print(f"{i:3}. {citation}")
        if len(citation) == 150:
            print("     ...")
        print()

    if len(citation_matches) > 25:
        print(f"... and {len(citation_matches) - 25} more")

    return len(citation_matches)


def main():
    """Run analysis."""

    print("\n🔬 IMPROVED CITATION FILTERING ANALYSIS")

    # First, analyze what's currently in the body text
    num_citations = analyze_body_text()

    print(f"\n{'=' * 80}")
    print("SUMMARY")
    print(f"{'=' * 80}\n")

    print(f"Found {num_citations} citation-like paragraphs in body text")
    print("These are likely labeled as 'text' or 'paragraph' rather than 'list_item'")
    print("\nRecommendation:")
    print("  - Expand filtering to check ALL labels for citation patterns")
    print("  - Not just 'list_item', but also 'text' and 'paragraph'")


if __name__ == "__main__":
    main()
