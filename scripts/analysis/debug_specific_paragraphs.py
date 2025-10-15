#!/usr/bin/env python3
"""Debug why specific paragraphs aren't being filtered."""

import re
from pathlib import Path

from extract_body_only import calculate_citation_density


def debug_paragraph(text: str):
    """Show detailed analysis of a paragraph."""

    density = calculate_citation_density(text)

    print(f"\nLength: {len(text)} chars")
    print(f"Citation density: {density:.2%}")
    print(f"First 150 chars: {text[:150]}...")

    # Check specific patterns
    patterns_found = []
    if re.search(r"\d+\s+U\.S\.\s+\d+", text):
        patterns_found.append("U.S. reporter")
    if re.search(r"\d+\s+S\.\s+Ct\.\s+\d+", text):
        patterns_found.append("S. Ct. reporter")
    if re.search(r"\d+\s+[A-Z][a-z]*\.\s+L\.\s+R[Ee][Vv]\.", text):
        patterns_found.append("Law review")
    if re.search(r"\(\d{4}\)", text):
        patterns_found.append("Year")
    if re.search(r"\bsupra note\s+\d+", text):
        patterns_found.append("supra note")
    if re.search(r"\binfra note\s+\d+", text):
        patterns_found.append("infra note")
    if re.search(r"\[hereinafter\s+", text):
        patterns_found.append("hereinafter")
    if re.match(r"^See\b", text):
        patterns_found.append("Starts with See")

    print(f"Citation patterns: {', '.join(patterns_found) if patterns_found else 'None'}")


def main():
    """Debug the two specific problematic paragraphs."""

    body_path = Path("results/body_extraction/Jackson_2014_default_body_only.txt")
    content = body_path.read_text(encoding="utf-8")
    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]

    print(f"\n{'=' * 80}")
    print("DEBUG SPECIFIC PARAGRAPHS")
    print(f"{'=' * 80}")

    # Find the two problematic paragraphs
    targets = [
        "The German  Constitutional  Court",
        "See Moshe Cohen-Eliya & Iddo Porat",
    ]

    for target in targets:
        for para in paragraphs:
            if target in para:
                print(f"\n{'=' * 80}")
                print(f"ANALYZING: {target}...")
                print(f"{'=' * 80}")
                debug_paragraph(para)
                print(f"\nFull text:\n{para}")
                break


if __name__ == "__main__":
    main()
