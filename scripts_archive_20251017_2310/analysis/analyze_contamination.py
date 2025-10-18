#!/usr/bin/env python3
"""Analyze contamination patterns in body text to improve filtering."""

import re
from pathlib import Path


def analyze_citation_density(text: str) -> dict:
    """Calculate what percentage of text consists of citations."""

    # Patterns that indicate citation content
    citation_patterns = [
        r"\d+\s+U\.S\.\s+\d+",  # Case citations
        r"\d+\s+S\.\s+Ct\.\s+\d+",
        r"\d+\s+[A-Z][a-z]*\.\s+L\.\s+R[Ee][Vv]\.",  # Law review citations
        r"\(\d{4}\)",  # Years in parens
        r"\bsupra note\s+\d+",  # Cross-references
        r"\binfra note\s+\d+",
        r"\[hereinafter\s+",  # Hereinafter clauses
        r"\bSee\s+generally",
        r"\bSee\s+also",
        r"\bSee\s+e\.g\.",
        r"\bCf\.",
        r"\bId\.\s+at",
    ]

    total_chars = len(text)
    citation_chars = 0

    for pattern in citation_patterns:
        matches = re.finditer(pattern, text)
        for match in matches:
            citation_chars += len(match.group())

    citation_density = citation_chars / total_chars if total_chars > 0 else 0

    # Count number of distinct citation patterns
    pattern_count = sum(1 for p in citation_patterns if re.search(p, text))

    return {
        "total_chars": total_chars,
        "citation_chars": citation_chars,
        "citation_density": citation_density,
        "pattern_count": pattern_count,
    }


def is_footnote_by_density(text: str, threshold: float = 0.20) -> bool:
    """
    Detect footnotes by citation density.

    If more than 20% of the text consists of citation markers,
    it's likely a footnote even if it has substantive content.
    """
    text = text.strip()

    # Skip very short items (already caught by other heuristics)
    if len(text) < 200:
        return False

    analysis = analyze_citation_density(text)

    # High citation density suggests footnote
    if analysis["citation_density"] > threshold:
        return True

    # Multiple citation patterns in moderate length text
    if analysis["pattern_count"] >= 3 and len(text) < 400:
        return True

    # Starts with citation signal AND has citations
    if re.match(r"^See\s+(generally|also|e\.g\.)", text) and analysis["pattern_count"] >= 2:
        return True

    return False


def analyze_body_text():
    """Analyze current body text for remaining citation-heavy paragraphs."""

    body_path = Path("results/body_extraction/Jackson_2014_default_body_only.txt")

    if not body_path.exists():
        print(f"❌ Body text file not found: {body_path}")
        return

    content = body_path.read_text(encoding="utf-8")
    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]

    print(f"\n{'=' * 80}")
    print("ANALYZING CITATION DENSITY IN BODY TEXT")
    print(f"{'=' * 80}\n")

    print(f"Total paragraphs: {len(paragraphs)}")

    # Analyze all paragraphs
    contamination = []

    for para in paragraphs:
        if len(para) > 200:  # Only check longer paragraphs
            analysis = analyze_citation_density(para)

            if analysis["citation_density"] > 0.15 or analysis["pattern_count"] >= 3:
                contamination.append(
                    {
                        "text": para[:200] + "..." if len(para) > 200 else para,
                        "full_length": len(para),
                        "density": analysis["citation_density"],
                        "patterns": analysis["pattern_count"],
                        "is_footnote": is_footnote_by_density(para),
                    }
                )

    print(f"Paragraphs with high citation density: {len(contamination)}")
    print(f"\n{'=' * 80}")
    print("TOP CONTAMINATION CANDIDATES")
    print(f"{'=' * 80}\n")

    # Sort by citation density
    contamination.sort(key=lambda x: x["density"], reverse=True)

    for i, item in enumerate(contamination[:20], 1):
        print(
            f"{i}. DENSITY: {item['density']:.2%} | PATTERNS: {item['patterns']} | "
            f"LEN: {item['full_length']} | FOOTNOTE: {item['is_footnote']}"
        )
        print(f"   {item['text']}")
        print()

    if len(contamination) > 20:
        print(f"... and {len(contamination) - 20} more\n")

    # Summary statistics
    would_filter = sum(1 for x in contamination if x["is_footnote"])

    print(f"\n{'=' * 80}")
    print("DENSITY-BASED FILTERING POTENTIAL")
    print(f"{'=' * 80}\n")
    print(f"High-density paragraphs found: {len(contamination)}")
    print(f"Would be filtered by density heuristic: {would_filter}")
    print(f"Would remain in body text: {len(contamination) - would_filter}")

    # Show what would remain
    if would_filter < len(contamination):
        print("\nParagraphs that would remain (false negatives):")
        for item in contamination:
            if not item["is_footnote"]:
                print(f"  - DENSITY: {item['density']:.2%} | {item['text'][:100]}...")


def main():
    """Run contamination analysis."""

    print("\n🔬 CITATION DENSITY ANALYSIS")
    analyze_body_text()


if __name__ == "__main__":
    main()
