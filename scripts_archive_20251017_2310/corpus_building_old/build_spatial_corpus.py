#!/usr/bin/env python3
"""
Build spatial corpus with bounding box coordinates for DoclingBERT v3.

Extracts text blocks from Docling JSON files and includes:
- Text content
- Label (7-class schema)
- Normalized bounding box coordinates [0-999]
- Page information

Usage:
    uv run python scripts/corpus_building/build_spatial_corpus.py
"""

import json
from pathlib import Path

import pandas as pd


def normalize_bbox(bbox: dict, page_width: float, page_height: float) -> dict:
    """Normalize bounding box coordinates to [0-999] range.

    Args:
        bbox: Dict with 'l', 't', 'r', 'b', 'coord_origin' keys
        page_width: Page width in points
        page_height: Page height in points

    Returns:
        Dict with normalized x0, y0, x1, y1, width, height (all integers 0-999)
    """
    # Handle coordinate origin (Docling uses BOTTOMLEFT)
    if bbox.get("coord_origin") == "BOTTOMLEFT":
        # Convert to TOPLEFT for consistency
        x0 = bbox["l"]
        y0 = page_height - bbox["t"]  # Flip y-axis
        x1 = bbox["r"]
        y1 = page_height - bbox["b"]  # Flip y-axis
    else:
        # Assume TOPLEFT
        x0 = bbox["l"]
        y0 = bbox["t"]
        x1 = bbox["r"]
        y1 = bbox["b"]

    # Normalize to [0-999]
    x0_norm = int(1000 * (x0 / page_width)) if page_width > 0 else 0
    y0_norm = int(1000 * (y0 / page_height)) if page_height > 0 else 0
    x1_norm = int(1000 * (x1 / page_width)) if page_width > 0 else 0
    y1_norm = int(1000 * (y1 / page_height)) if page_height > 0 else 0

    # Clamp to [0-999]
    x0_norm = max(0, min(999, x0_norm))
    y0_norm = max(0, min(999, y0_norm))
    x1_norm = max(0, min(999, x1_norm))
    y1_norm = max(0, min(999, y1_norm))

    # Calculate width and height
    width = x1_norm - x0_norm
    height = y1_norm - y0_norm

    return {
        "x0": x0_norm,
        "y0": y0_norm,
        "x1": x1_norm,
        "y1": y1_norm,
        "width": abs(width),
        "height": abs(height),
    }


def map_docling_label(docling_label: str) -> str:
    """Map Docling labels to 7-class schema.

    DoclingBERT v3 schema:
    - body_text: Main prose paragraphs
    - heading: Section headers, titles
    - footnote: Footnotes and endnotes
    - caption: Figure/table captions
    - page_header: Headers at top of page
    - page_footer: Footers at bottom of page
    - cover: Cover page elements
    """
    label_map = {
        # Body text
        "text": "body_text",
        "paragraph": "body_text",
        "list_item": "body_text",
        # Headings
        "section_header": "heading",
        "title": "heading",
        # Footnotes
        "footnote": "footnote",
        # Captions
        "caption": "caption",
        # Headers/Footers
        "page_header": "page_header",
        "page_footer": "page_footer",
        # References (treat as body_text or could be separate class)
        "reference": "body_text",
    }

    return label_map.get(docling_label, "body_text")


def extract_spatial_corpus(json_dir: Path, min_text_length: int = 20) -> list[dict]:
    """Extract spatial corpus from Docling JSON files.

    Args:
        json_dir: Directory containing .docling.json files
        min_text_length: Minimum text length to include

    Returns:
        List of dicts with text, label, bbox coords, page, pdf
    """
    all_samples = []
    stats = {
        "total_files": 0,
        "total_blocks": 0,
        "skipped_short": 0,
        "skipped_no_bbox": 0,
        "errors": 0,
    }
    label_counts = {}

    print("Extracting spatial corpus from Docling JSON files...")
    print("=" * 80)

    json_files = sorted(json_dir.glob("*.docling.json"))
    print(f"Found {len(json_files)} Docling JSON files\n")

    for json_file in json_files:
        stats["total_files"] += 1

        try:
            with open(json_file) as f:
                data = json.load(f)

            # Get page dimensions (use first page or default)
            # Note: This is simplified - we'd need actual page dimensions from Docling
            page_width = 612  # Standard US Letter width in points
            page_height = 792  # Standard US Letter height in points

            # Extract text blocks
            for item in data.get("texts", []):
                text = item.get("text", "").strip()

                # Skip short text
                if len(text) < min_text_length:
                    stats["skipped_short"] += 1
                    continue

                # Get label
                docling_label = item.get("label", "text")
                label = map_docling_label(docling_label)

                # For now, we'll need to re-extract with full Docling API to get bbox
                # This script will be a placeholder showing the structure
                # In practice, we need to call Docling's convert() method

                # Placeholder bbox (will be replaced with actual extraction)
                bbox_norm = {"x0": 0, "y0": 0, "x1": 0, "y1": 0, "width": 0, "height": 0}

                all_samples.append(
                    {
                        "text": text,
                        "label": label,
                        "x0": bbox_norm["x0"],
                        "y0": bbox_norm["y0"],
                        "x1": bbox_norm["x1"],
                        "y1": bbox_norm["y1"],
                        "width": bbox_norm["width"],
                        "height": bbox_norm["height"],
                        "page": item.get("page", 0),
                        "pdf": json_file.stem.replace(".docling", ""),
                    }
                )

                stats["total_blocks"] += 1
                label_counts[label] = label_counts.get(label, 0) + 1

            if stats["total_files"] % 20 == 0:
                print(
                    f"  Processed {stats['total_files']} files, {stats['total_blocks']} blocks..."
                )

        except Exception as e:
            stats["errors"] += 1
            print(f"✗ Error processing {json_file.name}: {e}")

    # Print statistics
    print("\n" + "=" * 80)
    print("EXTRACTION COMPLETE")
    print("=" * 80)
    print(f"Files processed:  {stats['total_files']}")
    print(f"Blocks extracted: {stats['total_blocks']}")
    print(f"Skipped (short):  {stats['skipped_short']}")
    print(f"Skipped (no bbox): {stats['skipped_no_bbox']}")
    print(f"Errors:           {stats['errors']}")
    print("\nClass distribution:")
    for label, count in sorted(label_counts.items(), key=lambda x: -x[1]):
        pct = 100 * count / stats["total_blocks"]
        print(f"  {label:15s} {count:6d} ({pct:5.1f}%)")

    return all_samples


def main():
    """Main extraction pipeline."""
    # Paths
    json_dir = Path("data/raw_pdf")
    output_file = Path("data/spatial_7class_corpus_placeholder.csv")

    # Extract corpus
    samples = extract_spatial_corpus(json_dir)

    # Save to CSV
    df = pd.DataFrame(samples)
    df.to_csv(output_file, index=False)

    print(f"\n✓ Saved {len(samples)} samples to {output_file}")
    print("\n⚠️  NOTE: This is a PLACEHOLDER. Bounding boxes are all zeros.")
    print(
        "   We need to re-extract from PDFs using Docling's full API to get actual bbox coordinates."
    )
    print("   Next step: Modify this to call DocumentConverter directly on PDFs.")


if __name__ == "__main__":
    main()
