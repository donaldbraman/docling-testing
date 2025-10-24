#!/usr/bin/env python3
"""
Generate HTML diff comparing ocrmac output at different DPIs.

Usage:
    uv run python scripts/evaluation/compare_dpi_outputs.py --pdf political_mootness --dpi1 300 --dpi2 600
"""

import argparse
import difflib
import json
from datetime import date
from pathlib import Path


def generate_html_diff(text1: str, text2: str, label1: str, label2: str, output_path: Path):
    """Generate HTML diff visualization between two texts."""
    # Split into lines for better diff visualization
    lines1 = text1.splitlines()
    lines2 = text2.splitlines()

    # Generate HTML diff
    differ = difflib.HtmlDiff(wrapcolumn=80)
    html = differ.make_file(
        lines1,
        lines2,
        fromdesc=label1,
        todesc=label2,
        context=True,
        numlines=3,
    )

    # Save to file
    with open(output_path, "w") as f:
        f.write(html)

    print(f"  ✓ Diff saved: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Compare ocrmac output at different DPIs")
    parser.add_argument("--pdf", required=True, help="PDF name (without .pdf extension)")
    parser.add_argument("--dpi1", type=int, required=True, help="First DPI to compare")
    parser.add_argument("--dpi2", type=int, required=True, help="Second DPI to compare")
    args = parser.parse_args()

    today = date.today().strftime("%Y%m%d")

    # Load comparison results
    result1_path = Path(f"results/ocr_comparison/{today}/{args.pdf}_{args.dpi1}dpi/comparison.json")
    result2_path = Path(f"results/ocr_comparison/{today}/{args.pdf}_{args.dpi2}dpi/comparison.json")

    if not result1_path.exists():
        print(f"Error: {result1_path} not found")
        return

    if not result2_path.exists():
        print(f"Error: {result2_path} not found")
        return

    # Load ocrmac normalized text
    with open(result1_path) as f:
        data1 = json.load(f)

    with open(result2_path) as f:
        data2 = json.load(f)

    text1 = data1["results"]["ocrmac"].get("normalized_text", "")
    text2 = data2["results"]["ocrmac"].get("normalized_text", "")

    if not text1 or not text2:
        print("Error: Could not extract normalized text from comparison results")
        return

    # Create output directory
    output_dir = Path(f"results/ocr_comparison/{today}/{args.pdf}_dpi_comparison")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate diff
    diff_file = output_dir / f"ocrmac_{args.dpi1}dpi_vs_{args.dpi2}dpi.html"

    print("\nGenerating DPI comparison diff...")
    print(f"  {args.pdf}")
    print(f"  {args.dpi1} DPI: {len(text1):,} chars")
    print(f"  {args.dpi2} DPI: {len(text2):,} chars")
    print()

    generate_html_diff(
        text1,
        text2,
        f"ocrmac {args.dpi1} DPI ({len(text1):,} chars)",
        f"ocrmac {args.dpi2} DPI ({len(text2):,} chars)",
        diff_file,
    )

    print(f"\n✓ Diff saved to: {diff_file}")


if __name__ == "__main__":
    main()
