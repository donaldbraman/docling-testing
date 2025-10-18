#!/usr/bin/env python3
"""Count HTML files by journal for journals with identified footnote patterns."""

from collections import defaultdict
from pathlib import Path


def identify_journal(filename: str) -> str:
    """Extract journal name from filename."""
    parts = filename.split("_")
    if not parts:
        return "unknown"

    # Handle multi-word journal names
    if parts[0] in ["bu", "boston"]:
        return "BU Law Review"
    elif parts[0] == "california":
        return "California Law Review"
    elif parts[0] == "michigan":
        return "Michigan Law Review"
    elif parts[0] == "supreme":
        return "Supreme Court Review"
    elif parts[0] == "harvard":
        return "Harvard Law Review"
    elif parts[0] == "texas":
        return "Texas Law Review"
    elif parts[0] == "columbia":
        return "Columbia Law Review"
    elif parts[0] == "chicago":
        return "University of Chicago Law Review"
    elif parts[0] == "virginia":
        return "Virginia Law Review"
    elif parts[0] == "usc":
        return "USC Law Review"
    elif parts[0] == "wisconsin":
        return "Wisconsin Law Review"
    elif parts[0] == "arxiv":
        return "Arxiv"
    elif parts[0] == "pmc":
        return "PMC"
    else:
        return parts[0].title()


def main():
    """Count HTML files for journals with extractable footnote patterns."""

    # Define journals with identified footnote patterns
    # Format: journal_name -> (pattern_type, pattern_description)
    journals_with_patterns = {
        "BU Law Review": ("[N] paragraphs", "<p> tags starting with [N]"),
        "California Law Review": ("[N] paragraphs", "<p> tags starting with [N]"),
        "Michigan Law Review": (
            "modern-footnotes",
            "<span class='modern-footnotes-footnote__note'>",
        ),
        "USC Law Review": ("modern-footnotes", "<span class='modern-footnotes-footnote__note'>"),
        "Supreme Court Review": ("NLM_fn", "<span class='NLM_fn'>"),
        "Harvard Law Review": ("superscript", "<sup> tags"),
        "Texas Law Review": ("superscript", "<sup> tags"),
        "Virginia Law Review": ("superscript", "<sup> tags"),
        "Wisconsin Law Review": ("superscript", "<sup> tags"),
        "Columbia Law Review": (
            "inline-js",
            "<button class='footnote-count'> + <span class='footnote-text'>",
        ),
        "University of Chicago Law Review": (
            "see-footnote",
            "<a class='see-footnote'> + <ul class='footnotes'>",
        ),
        # Non-law content (for diversity)
        "Arxiv": ("superscript", "<sup> tags"),
        "PMC": ("superscript", "<sup> tags"),
    }

    # Find all HTML files
    html_files = []
    for path in Path("data").rglob("*.html"):
        # Skip certain directories
        if "archived_abstract_only" in str(path):
            continue
        if "cover_pages" in str(path):
            continue
        if "pdf_content_visualizations" in str(path):
            continue
        html_files.append(path)

    # Group by journal
    by_journal = defaultdict(list)
    for html_path in html_files:
        journal = identify_journal(html_path.name)
        by_journal[journal].append(html_path)

    # Count files for journals with patterns
    print("HTML FILES BY JOURNAL (journals with extractable footnote patterns)")
    print("=" * 80)
    print()

    # Group by pattern type
    by_pattern = defaultdict(list)
    for journal, (pattern_type, _) in journals_with_patterns.items():
        if journal in by_journal:
            by_pattern[pattern_type].append(journal)

    total_files = 0
    total_law_files = 0
    total_non_law_files = 0

    for pattern_type in sorted(by_pattern.keys()):
        print(f"\n{pattern_type.upper()} PATTERN")
        print("-" * 80)

        journals_in_pattern = sorted(by_pattern[pattern_type])
        for journal in journals_in_pattern:
            count = len(by_journal[journal])
            pattern_desc = journals_with_patterns[journal][1]

            print(f"  {journal:40} {count:>3} files")
            print(f"    Pattern: {pattern_desc}")

            total_files += count
            if journal in ["Arxiv", "PMC"]:
                total_non_law_files += count
            else:
                total_law_files += count

    # Summary
    print(f"\n{'=' * 80}")
    print("SUMMARY")
    print(f"{'=' * 80}")
    print(f"Law review HTML files:     {total_law_files:>3}")
    print(f"Non-law HTML files (STEM): {total_non_law_files:>3}")
    print(f"Total usable HTML files:   {total_files:>3}")
    print()
    print(
        f"Journals with patterns:    {len([j for j in journals_with_patterns if j not in ['Arxiv', 'PMC']])}"
    )
    print(f"Pattern types identified:  {len({p[0] for p in journals_with_patterns.values()})}")


if __name__ == "__main__":
    main()
