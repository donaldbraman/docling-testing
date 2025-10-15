#!/usr/bin/env python3
"""Test the improved density-based citation filter on existing body text."""

from pathlib import Path

from extract_body_only import is_likely_citation


def test_on_existing_body_text():
    """Test improved filter on current body text."""

    body_path = Path("results/body_extraction/Jackson_2014_default_body_only.txt")
    content = body_path.read_text(encoding="utf-8")
    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]

    print(f"\n{'=' * 80}")
    print("TESTING IMPROVED DENSITY FILTER")
    print(f"{'=' * 80}\n")

    print(f"Total paragraphs in current body text: {len(paragraphs)}")

    # Test the known contamination examples
    contamination_examples = [
        "The German  Constitutional  Court  has been particularly influential",
        "See Moshe Cohen-Eliya & Iddo Porat, The Hidden Foreign  Law Debate in Heller",
        "State  Farm  Mut.  Auto.  Ins.  Co.  v.  Campbell,  538  U.S. 408",
    ]

    print("\nTesting known contamination examples:")
    print("-" * 80)

    for example in contamination_examples:
        # Find the full paragraph
        for para in paragraphs:
            if example in para:
                would_filter = is_likely_citation(para)
                print(f"\n{'WOULD FILTER' if would_filter else 'WOULD KEEP'}: {para[:100]}...")
                print(f"Length: {len(para)} chars")
                break

    # Count how many paragraphs would be filtered
    would_filter = [p for p in paragraphs if is_likely_citation(p)]

    print(f"\n{'=' * 80}")
    print("FILTER RESULTS")
    print(f"{'=' * 80}\n")

    print(f"Paragraphs that would be FILTERED: {len(would_filter)}")
    print(f"Paragraphs that would REMAIN: {len(paragraphs) - len(would_filter)}")

    if would_filter:
        print("\nSample filtered paragraphs:")
        for i, para in enumerate(would_filter[:10], 1):
            print(f"\n{i}. {para[:150]}...")

    # Calculate what would remain
    remaining_words = sum(len(p.split()) for p in paragraphs if not is_likely_citation(p))
    total_words = sum(len(p.split()) for p in paragraphs)

    print(f"\n{'=' * 80}")
    print("WORD COUNT IMPACT")
    print(f"{'=' * 80}\n")
    print(f"Current body text: {total_words:,} words")
    print(f"After density filtering: {remaining_words:,} words")
    print(
        f"Would remove: {total_words - remaining_words:,} words ({100 * (total_words - remaining_words) / total_words:.1f}%)"
    )


if __name__ == "__main__":
    test_on_existing_body_text()
