#!/usr/bin/env python3
"""Show layout elements detected by Docling in a readable format."""

import json
from pathlib import Path


def show_layout_from_json(json_path: Path):
    """Display layout analysis from saved JSON."""

    if not json_path.exists():
        print(f"❌ File not found: {json_path}")
        return

    data = json.loads(json_path.read_text())

    print(f"\n{'='*80}")
    print(f"LAYOUT ANALYSIS: {data['filename']}")
    print(f"{'='*80}\n")

    print(f"Total elements detected: {data['total_elements']}")
    print(f"\nElement breakdown:")

    for label, count in sorted(data['element_counts'].items(), key=lambda x: -x[1]):
        print(f"  {label:30} : {count:>4}")

    print(f"\nFootnote boxes detected: {data.get('footnote_count', 0)}")
    print(f"Header boxes detected: {data.get('header_count', 0)}")
    print(f"Footer boxes detected: {data.get('footer_count', 0)}")

    # Show sample items
    print(f"\n{'='*80}")
    print("SAMPLE ELEMENTS (first 10):")
    print(f"{'='*80}\n")

    for i, item in enumerate(data['sample_items'][:10], 1):
        print(f"{i}. {item['label']} (level {item.get('level', '?')})")
        if item['text_preview']:
            print(f"   Text: {item['text_preview'][:100]}...")
        print()


def main():
    """Show layout from most recent analysis."""

    base_dir = Path(__file__).parent
    layout_dir = base_dir / "results" / "layout_analysis_v2"

    if not layout_dir.exists():
        print(f"❌ Layout directory not found: {layout_dir}")
        return

    # Find all layout JSON files
    json_files = sorted(layout_dir.glob("*_layout.json"))

    if not json_files:
        print("❌ No layout analysis files found")
        return

    # Show each
    for json_file in json_files:
        show_layout_from_json(json_file)


if __name__ == "__main__":
    main()
