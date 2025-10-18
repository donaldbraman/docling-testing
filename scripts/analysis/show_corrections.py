#!/usr/bin/env python3
"""
Show corrections from CSV alignment file.

Usage:
    python show_corrections.py <basename> [limit]
"""

import csv
import sys
from pathlib import Path


def show_corrections(basename: str, limit: int = 20):
    """Show corrections from CSV."""

    csv_file = Path(f"data/v3_data/v3_csv/{basename}.csv")
    if not csv_file.exists():
        print(f"❌ CSV not found: {csv_file}")
        return

    count = 0
    with open(csv_file, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if (
                row["match_status"] == "matched"
                and row["pdf_original_label"] != row["pdf_corrected_label"]
            ):
                count += 1
                print(f"Correction #{count}:")
                print(f"  Page: {row['page_no']}")
                print(f"  Original label: {row['pdf_original_label']}")
                print(f"  Corrected label: {row['pdf_corrected_label']}")
                print(f"  Confidence: {row['match_confidence']}%")
                print(f"  PDF text: {row['pdf_text'][:200]}")

                # Show which HTML matched
                if row.get("matched_html_body"):
                    print(f"  HTML body match: {row['matched_html_body'][:200]}")
                if row.get("matched_html_footnote"):
                    print(f"  HTML fn match: {row['matched_html_footnote'][:200]}")

                print()

                if count >= limit:
                    break

    print(f"Total corrections shown: {count}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python show_corrections.py <basename> [limit]")
        sys.exit(1)

    basename = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 20

    show_corrections(basename, limit)
