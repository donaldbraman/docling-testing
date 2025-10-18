#!/usr/bin/env python3
"""Analyze actual citation density distribution in body text vs footnotes."""

import re
from collections import defaultdict
from pathlib import Path


def calculate_citation_density(text: str) -> float:
    """Calculate what percentage of text consists of citation markers."""
    citation_patterns = [
        r"\d+\s+U\.S\.\s+\d+",
        r"\d+\s+S\.\s+Ct\.\s+\d+",
        r"\d+\s+[A-Z][a-z]*\.\s+L\.\s+R[Ee][Vv]\.",
        r"\(\d{4}\)",
        r"\bsupra note\s+\d+",
        r"\binfra note\s+\d+",
        r"\[hereinafter\s+",
    ]

    total_chars = len(text)
    if total_chars == 0:
        return 0.0

    citation_chars = 0
    for pattern in citation_patterns:
        for match in re.finditer(pattern, text):
            citation_chars += len(match.group())

    return citation_chars / total_chars


def analyze_densities(all_text_path: Path, body_only_path: Path, footnotes_path: Path):
    """Analyze citation density distribution in body vs footnotes."""

    # Read files
    all_text = all_text_path.read_text(encoding="utf-8")
    body_text = body_only_path.read_text(encoding="utf-8")
    footnote_text = footnotes_path.read_text(encoding="utf-8")

    # Split into paragraphs
    all_paras = [p.strip() for p in all_text.split("\n\n") if p.strip()]
    body_paras = [p.strip() for p in body_text.split("\n\n") if p.strip()]
    footnote_paras = [p.strip() for p in footnote_text.split("\n\n") if p.strip()]

    # Calculate densities
    print(f"\n{'=' * 80}")
    print("CITATION DENSITY ANALYSIS")
    print(f"{'=' * 80}\n")

    # Body text densities
    body_densities = [calculate_citation_density(p) for p in body_paras if len(p) >= 200]
    footnote_densities = [calculate_citation_density(p) for p in footnote_paras if len(p) >= 200]

    print("BODY TEXT (paragraphs >= 200 chars):")
    print(f"  Count: {len(body_densities)}")
    if body_densities:
        print(f"  Mean density: {sum(body_densities) / len(body_densities):.1%}")
        print(f"  Median: {sorted(body_densities)[len(body_densities) // 2]:.1%}")
        print(f"  Max: {max(body_densities):.1%}")
        print(f"  Min: {min(body_densities):.1%}")
        print("\n  Distribution:")
        buckets = defaultdict(int)
        for d in body_densities:
            bucket = int(d * 100 / 5) * 5  # Round to nearest 5%
            buckets[bucket] += 1
        for bucket in sorted(buckets.keys()):
            bar = "█" * (buckets[bucket] // 5 if buckets[bucket] >= 5 else 1)
            print(f"    {bucket:3d}%-{bucket + 4:3d}%: {buckets[bucket]:3d} {bar}")

    print("\nFOOTNOTES (paragraphs >= 200 chars):")
    print(f"  Count: {len(footnote_densities)}")
    if footnote_densities:
        print(f"  Mean density: {sum(footnote_densities) / len(footnote_densities):.1%}")
        print(f"  Median: {sorted(footnote_densities)[len(footnote_densities) // 2]:.1%}")
        print(f"  Max: {max(footnote_densities):.1%}")
        print(f"  Min: {min(footnote_densities):.1%}")
        print("\n  Distribution:")
        buckets = defaultdict(int)
        for d in footnote_densities:
            bucket = int(d * 100 / 5) * 5
            buckets[bucket] += 1
        for bucket in sorted(buckets.keys()):
            bar = "█" * (buckets[bucket] // 2 if buckets[bucket] >= 2 else 1)
            print(f"    {bucket:3d}%-{bucket + 4:3d}%: {buckets[bucket]:3d} {bar}")

    # Find the overlap zone
    if body_densities and footnote_densities:
        max_body = max(body_densities)
        min_footnote = min(footnote_densities)
        print(f"\n{'=' * 80}")
        print("OVERLAP ANALYSIS:")
        print(f"{'=' * 80}\n")
        print(f"  Highest body density: {max_body:.1%}")
        print(f"  Lowest footnote density: {min_footnote:.1%}")
        print("  Current threshold: 20.0%")
        print(f"\n  Body paragraphs above 20%: {sum(1 for d in body_densities if d > 0.20)}")
        print(f"  Footnotes below 20%: {sum(1 for d in footnote_densities if d < 0.20)}")

        # Show examples of body text above threshold
        print(f"\n{'=' * 80}")
        print("BODY PARAGRAPHS ABOVE 20% THRESHOLD:")
        print(f"{'=' * 80}\n")
        for para in body_paras:
            if len(para) >= 200:
                density = calculate_citation_density(para)
                if density > 0.20:
                    print(f"  Density: {density:.1%}")
                    print(f"  Length: {len(para)} chars")
                    print(f"  Preview: {para[:150]}...")
                    print()


if __name__ == "__main__":
    base_dir = Path(__file__).parent
    results = base_dir / "results" / "body_extraction"

    all_text = results / "Jackson_2014_default_all.txt"
    body_only = results / "Jackson_2014_default_body_only.txt"
    footnotes = results / "Jackson_2014_default_footnotes_only.txt"

    if all([f.exists() for f in [all_text, body_only, footnotes]]):
        analyze_densities(all_text, body_only, footnotes)
    else:
        print("❌ Required files not found")
