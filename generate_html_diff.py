#!/usr/bin/env python3
"""Generate HTML diff comparing full text vs body-only text."""

import difflib
from pathlib import Path


def generate_html_diff(file_a: Path, file_b: Path, output_file: Path):
    """Generate an HTML diff between two text files."""

    # Read the files
    text_a = file_a.read_text(encoding='utf-8')
    text_b = file_b.read_text(encoding='utf-8')

    # Split into lines
    lines_a = text_a.splitlines(keepends=True)
    lines_b = text_b.splitlines(keepends=True)

    # Generate HTML diff
    diff = difflib.HtmlDiff(wrapcolumn=80)
    html = diff.make_file(
        lines_a,
        lines_b,
        fromdesc=f"All Text ({file_a.name})",
        todesc=f"Body Only ({file_b.name})",
        context=True,
        numlines=3
    )

    # Write output
    output_file.write_text(html, encoding='utf-8')
    print(f"✅ HTML diff saved to: {output_file}")
    print(f"   Comparing: {file_a.name} → {file_b.name}")


def main():
    """Generate HTML diff for Jackson_2014 full text vs body text."""

    base_dir = Path(__file__).parent
    results_dir = base_dir / "results" / "body_extraction"

    # Files to compare
    all_text = results_dir / "Jackson_2014_default_all.txt"
    body_only = results_dir / "Jackson_2014_default_body_only.txt"

    # Output file
    output_dir = base_dir / "results" / "diffs"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "Jackson_2014_all_vs_body.html"

    # Generate diff
    print("\n" + "="*80)
    print("GENERATING HTML DIFF")
    print("="*80)
    print(f"\nComparing:")
    print(f"  All text:  {all_text}")
    print(f"  Body only: {body_only}")
    print()

    generate_html_diff(all_text, body_only, output_file)

    print(f"\n🌐 Open in browser:")
    print(f"   file://{output_file.absolute()}")


if __name__ == "__main__":
    main()
