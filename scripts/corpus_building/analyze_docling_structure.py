#!/usr/bin/env python3
"""
Analyze Docling extraction structure to understand text layers and labels.

This script examines a Docling extraction to identify:
1. All unique label types in the texts array
2. All unique content_layer values
3. Parent/children hierarchy patterns
4. Which labels likely correspond to body_text vs footnotes
5. Text distribution across labels

Author: Claude Code
Date: 2025-01-18
"""

import json
from collections import Counter, defaultdict
from pathlib import Path


def analyze_docling_extraction(json_file: Path):
    """
    Deep analysis of Docling extraction structure.

    Args:
        json_file: Path to Docling extraction JSON
    """
    print(f"\n{'=' * 80}")
    print(f"Analyzing: {json_file.name}")
    print(f"{'=' * 80}")

    with open(json_file) as f:
        data = json.load(f)

    # Top-level structure
    print("\n📋 Top-level keys:")
    for key in data:
        if isinstance(data[key], list):
            print(f"  {key}: list with {len(data[key])} items")
        elif isinstance(data[key], dict):
            print(f"  {key}: dict")
        else:
            print(f"  {key}: {type(data[key]).__name__}")

    # Analyze texts array
    texts = data.get("texts", [])
    print(f"\n📝 Texts array: {len(texts)} items")

    # Count labels
    label_counts = Counter(item.get("label") for item in texts)
    print("\n🏷️  Label distribution:")
    for label, count in label_counts.most_common():
        print(f"  {label:25s}: {count:4d} items")

    # Count content_layer values
    content_layer_counts = Counter(item.get("content_layer") for item in texts)
    print("\n🔍 Content layer distribution:")
    for layer, count in content_layer_counts.most_common():
        print(f"  {layer:25s}: {count:4d} items")

    # Analyze text lengths by label
    label_text_stats = defaultdict(list)
    for item in texts:
        label = item.get("label", "unknown")
        text = item.get("text", "")
        label_text_stats[label].append(len(text))

    print("\n📊 Text length statistics by label:")
    for label in sorted(label_text_stats.keys()):
        lengths = label_text_stats[label]
        avg_len = sum(lengths) / len(lengths)
        min_len = min(lengths)
        max_len = max(lengths)
        print(f"  {label:25s}: avg={avg_len:7.1f}, min={min_len:5d}, max={max_len:5d}")

    # Look for footnote patterns
    print("\n🔎 Searching for footnote-related patterns...")
    footnote_candidates = []
    for idx, item in enumerate(texts):
        label = item.get("label", "")
        text = item.get("text", "").lower()

        # Check if label or text contains 'footnote', 'note', 'fn'
        if any(keyword in label.lower() for keyword in ["footnote", "note", "fn"]) or any(
            keyword in text for keyword in ["footnote", "see supra", "see infra"]
        ):
            footnote_candidates.append((idx, label, item.get("text", "")[:100]))

    if footnote_candidates:
        print(f"  Found {len(footnote_candidates)} potential footnote items:")
        for idx, label, text_preview in footnote_candidates[:10]:  # Show first 10
            print(f"    [{idx}] {label}: {text_preview}...")
    else:
        print("  ⚠️  No obvious footnote labels found")

    # Analyze parent/children hierarchy
    print("\n🌳 Parent/children hierarchy:")
    items_with_children = [item for item in texts if item.get("children")]
    items_with_no_children = [item for item in texts if not item.get("children")]
    print(f"  Items with children: {len(items_with_children)}")
    print(f"  Items with no children (leaves): {len(items_with_no_children)}")

    # Show example of hierarchy
    if items_with_children:
        example = items_with_children[0]
        print("\n  Example parent item:")
        print(f"    Label: {example.get('label')}")
        print(f"    Text: {example.get('text', '')[:80]}...")
        print(f"    Children refs: {example.get('children', [])[:3]}...")

    # Analyze provenance (page distribution)
    page_distribution = defaultdict(int)
    for item in texts:
        prov = item.get("prov", [])
        if prov and isinstance(prov, list):
            page_no = prov[0].get("page_no")
            if page_no:
                page_distribution[page_no] += 1

    print("\n📄 Page distribution:")
    for page in sorted(page_distribution.keys())[:10]:  # Show first 10 pages
        print(f"  Page {page}: {page_distribution[page]} text items")
    if len(page_distribution) > 10:
        print(f"  ... and {len(page_distribution) - 10} more pages")

    # Check body structure
    body = data.get("body", {})
    print("\n📚 Body structure:")
    print(f"  Label: {body.get('label')}")
    print(f"  Content layer: {body.get('content_layer')}")
    print(f"  Children count: {len(body.get('children', []))}")

    # Analyze tables
    tables = data.get("tables", [])
    print(f"\n📊 Tables: {len(tables)} items")

    # Analyze pictures
    pictures = data.get("pictures", [])
    print(f"\n🖼️  Pictures: {len(pictures)} items")

    # Sample a few text items to show full structure
    print("\n🔬 Sample text items (first 3):")
    for idx in range(min(3, len(texts))):
        item = texts[idx]
        print(f"\n  Item {idx}:")
        print(f"    Label: {item.get('label')}")
        print(f"    Content layer: {item.get('content_layer')}")
        print(f"    Text: {item.get('text', '')[:100]}...")
        print(f"    Has parent: {'parent' in item}")
        print(f"    Has children: {len(item.get('children', []))} children")
        print(f"    Provenance: {len(item.get('prov', []))} bbox entries")


def main():
    """Analyze the first Docling extraction."""
    extraction_dir = Path("data/v3_data/docling_extraction")

    # Get first JSON file
    json_files = sorted(extraction_dir.glob("*.json"))
    if not json_files:
        print("❌ No extraction files found in data/v3_data/docling_extraction/")
        return

    print(f"Found {len(json_files)} extraction file(s)")

    # Analyze first file
    analyze_docling_extraction(json_files[0])


if __name__ == "__main__":
    main()
