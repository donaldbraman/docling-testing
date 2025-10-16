#!/usr/bin/env python3
"""
Build spatial corpus with actual bounding box coordinates for DoclingBERT v3.

Re-extracts from PDFs using Docling to get bbox data.

Usage:
    uv run python scripts/corpus_building/build_spatial_corpus_v3.py
"""

from pathlib import Path

import pandas as pd
from docling.document_converter import DocumentConverter


def map_docling_label(docling_label: str) -> str:
    """Map Docling labels to 7-class schema."""
    label_map = {
        "text": "body_text",
        "paragraph": "body_text",
        "list_item": "body_text",
        "section_header": "heading",
        "title": "heading",
        "footnote": "footnote",
        "caption": "caption",
        "page_header": "page_header",
        "page_footer": "page_footer",
        "reference": "body_text",
    }
    return label_map.get(docling_label, "body_text")


def extract_spatial_corpus(
    pdf_dir: Path, min_text_length: int = 20, max_pdfs: int = None
) -> list[dict]:
    """Extract spatial corpus from PDFs with bbox coordinates.

    Args:
        pdf_dir: Directory containing PDF files
        min_text_length: Minimum text length to include
        max_pdfs: Maximum number of PDFs to process (None = all)

    Returns:
        List of dicts with text, label, bbox coords, page, pdf
    """
    converter = DocumentConverter()
    all_samples = []

    stats = {
        "total_files": 0,
        "total_blocks": 0,
        "skipped_short": 0,
        "skipped_no_bbox": 0,
        "errors": 0,
    }
    label_counts = {}

    print("Extracting spatial corpus from PDFs with Docling...")
    print("=" * 80)

    pdf_files = sorted(pdf_dir.glob("*.pdf"))
    if max_pdfs:
        pdf_files = pdf_files[:max_pdfs]

    print(f"Processing {len(pdf_files)} PDF files\n")

    for pdf_file in pdf_files:
        stats["total_files"] += 1

        try:
            # Convert PDF with Docling
            result = converter.convert(pdf_file)

            # Get page dimensions from first page (fallback to standard)
            page_width = 612  # US Letter width in points
            page_height = 792  # US Letter height in points

            # Try to get actual dimensions if available
            if hasattr(result, "document") and hasattr(result.document, "pages"):
                if len(result.document.pages) > 0:
                    first_page = result.document.pages[0]
                    if hasattr(first_page, "size"):
                        page_width = first_page.size.width
                        page_height = first_page.size.height

            # Extract text blocks with bbox
            for item in result.document.texts:
                text = item.text.strip() if hasattr(item, "text") else ""

                # Skip short text
                if len(text) < min_text_length:
                    stats["skipped_short"] += 1
                    continue

                # Get label
                docling_label = str(item.label) if hasattr(item, "label") else "text"
                label = map_docling_label(docling_label)

                # Get bbox if available
                if hasattr(item, "bbox") and item.bbox:
                    bbox = item.bbox

                    # Handle coordinate origin
                    if hasattr(bbox, "coord_origin") and bbox.coord_origin == "BOTTOMLEFT":
                        # Convert to TOPLEFT
                        x0 = bbox.l
                        y0 = page_height - bbox.t
                        x1 = bbox.r
                        y1 = page_height - bbox.b
                    else:
                        x0 = bbox.l if hasattr(bbox, "l") else 0
                        y0 = bbox.t if hasattr(bbox, "t") else 0
                        x1 = bbox.r if hasattr(bbox, "r") else 0
                        y1 = bbox.b if hasattr(bbox, "b") else 0

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

                    width = abs(x1_norm - x0_norm)
                    height = abs(y1_norm - y0_norm)
                else:
                    # No bbox available
                    stats["skipped_no_bbox"] += 1
                    continue

                # Get page number
                page = item.page if hasattr(item, "page") else 0

                all_samples.append(
                    {
                        "text": text,
                        "label": label,
                        "x0": x0_norm,
                        "y0": y0_norm,
                        "x1": x1_norm,
                        "y1": y1_norm,
                        "width": width,
                        "height": height,
                        "page": page,
                        "pdf": pdf_file.stem,
                    }
                )

                stats["total_blocks"] += 1
                label_counts[label] = label_counts.get(label, 0) + 1

            if stats["total_files"] % 10 == 0:
                print(
                    f"  Processed {stats['total_files']}/{len(pdf_files)} PDFs, {stats['total_blocks']} blocks..."
                )

        except Exception as e:
            stats["errors"] += 1
            print(f"✗ Error processing {pdf_file.name}: {e}")

    # Print statistics
    print("\n" + "=" * 80)
    print("EXTRACTION COMPLETE")
    print("=" * 80)
    print(f"Files processed:   {stats['total_files']}")
    print(f"Blocks extracted:  {stats['total_blocks']}")
    print(f"Skipped (short):   {stats['skipped_short']}")
    print(f"Skipped (no bbox): {stats['skipped_no_bbox']}")
    print(f"Errors:            {stats['errors']}")
    print("\nClass distribution:")
    for label, count in sorted(label_counts.items(), key=lambda x: -x[1]):
        pct = 100 * count / stats["total_blocks"] if stats["total_blocks"] > 0 else 0
        print(f"  {label:15s} {count:6d} ({pct:5.1f}%)")

    return all_samples


def balance_corpus(samples: list[dict], target_per_class: int = 2000) -> list[dict]:
    """Balance corpus by oversampling minority classes.

    Args:
        samples: All extracted samples
        target_per_class: Target number of samples per class

    Returns:
        Balanced list of samples
    """
    import random
    from collections import defaultdict

    # Group by label
    by_label = defaultdict(list)
    for sample in samples:
        by_label[sample["label"]].append(sample)

    balanced = []
    print("\nBalancing corpus...")
    for label, label_samples in sorted(by_label.items()):
        count = len(label_samples)

        if count >= target_per_class:
            # Random sample if we have too many
            selected = random.sample(label_samples, target_per_class)
        else:
            # Oversample if we have too few
            selected = label_samples.copy()
            while len(selected) < target_per_class:
                selected.extend(
                    random.sample(label_samples, min(count, target_per_class - len(selected)))
                )

        balanced.extend(selected)
        print(f"  {label:15s} {count:6d} → {len(selected):6d}")

    # Shuffle
    random.shuffle(balanced)
    print(f"\nTotal balanced corpus: {len(balanced)} samples")

    return balanced


def main():
    """Main extraction pipeline."""
    import argparse

    parser = argparse.ArgumentParser(description="Build spatial corpus for DoclingBERT v3")
    parser.add_argument("--max-pdfs", type=int, default=None, help="Max PDFs to process")
    parser.add_argument(
        "--target-per-class", type=int, default=2000, help="Target samples per class"
    )
    parser.add_argument("--no-balance", action="store_true", help="Don't balance classes")
    args = parser.parse_args()

    # Paths
    pdf_dir = Path("data/raw_pdf")
    output_file = Path("data/spatial_7class_corpus.csv")

    # Extract corpus
    print(f"Extracting from: {pdf_dir}")
    print(f"Max PDFs: {args.max_pdfs or 'all'}")
    print("")

    samples = extract_spatial_corpus(pdf_dir, max_pdfs=args.max_pdfs)

    if not samples:
        print("\n✗ No samples extracted. Check PDF directory and Docling output.")
        return

    # Balance if requested
    if not args.no_balance:
        samples = balance_corpus(samples, target_per_class=args.target_per_class)

    # Save to CSV
    df = pd.DataFrame(samples)
    df.to_csv(output_file, index=False)

    print(f"\n✓ Saved {len(samples)} samples to {output_file}")
    print(f"\nColumns: {list(df.columns)}")
    print("\nSample row:")
    print(df.head(1).to_dict("records")[0])


if __name__ == "__main__":
    main()
