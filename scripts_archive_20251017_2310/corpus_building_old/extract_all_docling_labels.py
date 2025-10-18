#!/usr/bin/env python3
"""
Extract ALL paragraphs from PDFs with Docling's native labels.

Saves complete Docling extractions including:
- page_header, page_footer
- reference (bibliography)
- caption
- footnote
- text, paragraph, list_item
- section_header, title

This preserves all structure for multi-class training.
"""

from pathlib import Path

import pandas as pd
from docling.document_converter import DocumentConverter


def extract_all_docling_paragraphs(pdf_dir: Path) -> list[dict]:
    """Extract all paragraphs with Docling's native labels.

    Returns:
        List of dicts with 'text', 'docling_label', 'source', 'page' keys
    """
    converter = DocumentConverter()
    all_samples = []

    stats = {
        "total_pdfs": 0,
        "total_paragraphs": 0,
        "errors": 0,
    }
    label_counts = {}

    print("Extracting ALL Docling paragraphs from PDFs...")
    print("=" * 80)

    for pdf_path in sorted(pdf_dir.glob("*.pdf")):
        stats["total_pdfs"] += 1

        try:
            # Extract with Docling
            result = converter.convert(pdf_path)

            # Get all document items with labels
            for item in result.document.texts:
                if hasattr(item, "label") and hasattr(item, "text"):
                    label = str(item.label)
                    text = item.text.strip()

                    # Skip very short items (< 20 chars)
                    if len(text) < 20:
                        continue

                    # Get page number if available
                    page = getattr(item, "page", None)

                    all_samples.append(
                        {
                            "text": text,
                            "docling_label": label,
                            "source": pdf_path.name,
                            "page": page,
                        }
                    )

                    stats["total_paragraphs"] += 1
                    label_counts[label] = label_counts.get(label, 0) + 1

            if stats["total_pdfs"] % 10 == 0:
                print(
                    f"  Processed {stats['total_pdfs']} PDFs, {stats['total_paragraphs']} paragraphs..."
                )

        except Exception as e:
            stats["errors"] += 1
            print(f"✗ Error with {pdf_path.name}: {e}")

    print("\n" + "=" * 80)
    print("EXTRACTION SUMMARY")
    print("=" * 80)
    print(f"Total PDFs processed:  {stats['total_pdfs']}")
    print(f"Total paragraphs:      {stats['total_paragraphs']}")
    print(f"Errors:                {stats['errors']}")

    print("\nLabel distribution:")
    for label, count in sorted(label_counts.items(), key=lambda x: -x[1]):
        percentage = (count / stats["total_paragraphs"]) * 100
        print(f"  {label:20s} {count:6,} ({percentage:5.1f}%)")

    return all_samples


def main():
    """Extract all Docling paragraphs and save."""
    base_dir = Path(__file__).parent
    pdf_dir = Path("/Users/donaldbraman/Documents/GitHub/12-factor-agents/test_corpus/pdfs")
    output_path = base_dir / "data" / "full_docling_corpus.csv"

    if not pdf_dir.exists():
        print(f"Error: PDF directory not found: {pdf_dir}")
        return

    # Extract all paragraphs
    all_samples = extract_all_docling_paragraphs(pdf_dir)

    if not all_samples:
        print("\nNo paragraphs extracted!")
        return

    # Save as CSV
    df = pd.DataFrame(all_samples)
    output_path.parent.mkdir(exist_ok=True)
    df.to_csv(output_path, index=False)

    print(f"\n✓ Full Docling corpus saved to: {output_path}")
    print(f"  {len(df):,} total paragraphs")

    # Show breakdown by useful categories
    print("\n" + "=" * 80)
    print("USEFUL CATEGORIES FOR TRAINING")
    print("=" * 80)

    useful_labels = {
        "footnote": "Footnotes (citations)",
        "page_header": "Page headers",
        "page_footer": "Page footers",
        "reference": "Bibliography/references",
        "caption": "Figure/table captions",
        "text": "Body text",
        "paragraph": "Body paragraphs",
        "list_item": "List items",
        "section_header": "Section headers",
        "title": "Document titles",
    }

    for label, description in useful_labels.items():
        count = len(df[df["docling_label"] == label])
        if count > 0:
            print(f"  {label:20s} {count:6,}  - {description}")


if __name__ == "__main__":
    main()
