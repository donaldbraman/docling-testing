#!/usr/bin/env python3
"""Show footnote counts for all articles in labeled_html_v2."""

import json
from collections import defaultdict
from pathlib import Path


def main():
    """Display footnote counts for all enhanced HTML extractions."""
    labeled_html_dir = Path("data/labeled_html_v2")

    if not labeled_html_dir.exists():
        print(f"❌ Directory not found: {labeled_html_dir}")
        return

    json_files = sorted(labeled_html_dir.glob("*.json"))

    print("FOOTNOTE COUNTS FROM ENHANCED HTML EXTRACTION (v2)")
    print("=" * 80)
    print(f"Total articles: {len(json_files)}\n")

    by_journal = defaultdict(list)

    for json_file in json_files:
        with open(json_file) as f:
            data = json.load(f)

        basename = data["basename"]
        journal = data["journal"]
        stats = data["stats"]

        by_journal[journal].append(
            {
                "basename": basename,
                "body": stats["body_text"],
                "footnotes": stats["footnote_text"],
                "total_words": stats["total_words"],
            }
        )

    # Display by journal
    for journal in sorted(by_journal.keys()):
        articles = by_journal[journal]
        print(f"\n{journal} ({len(articles)} articles)")
        print("-" * 80)

        for article in articles:
            print(f"  {article['basename'][:60]}")
            print(f"    Body paragraphs:     {article['body']:>4}")
            print(f"    Footnote paragraphs: {article['footnotes']:>4}")
            print(f"    Total words:         {article['total_words']:>6,}")
            print()

        # Summary for journal
        total_body = sum(a["body"] for a in articles)
        total_footnotes = sum(a["footnotes"] for a in articles)
        total_words = sum(a["total_words"] for a in articles)

        print("  JOURNAL TOTAL:")
        print(f"    Body paragraphs:     {total_body:>4}")
        print(f"    Footnote paragraphs: {total_footnotes:>4}")
        print(f"    Total words:         {total_words:>6,}")
        print()

    # Grand total
    all_articles = [a for articles in by_journal.values() for a in articles]
    grand_total_body = sum(a["body"] for a in all_articles)
    grand_total_footnotes = sum(a["footnotes"] for a in all_articles)
    grand_total_words = sum(a["total_words"] for a in all_articles)

    print("=" * 80)
    print("GRAND TOTAL:")
    print(f"  Articles:            {len(all_articles):>4}")
    print(f"  Body paragraphs:     {grand_total_body:>4}")
    print(f"  Footnote paragraphs: {grand_total_footnotes:>4}")
    print(f"  Total words:         {grand_total_words:>6,}")


if __name__ == "__main__":
    main()
