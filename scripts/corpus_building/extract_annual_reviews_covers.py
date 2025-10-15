#!/usr/bin/env python3
"""
Extract Annual Reviews cover pages from PDFs.

Processes only Annual Reviews PDFs (annurev-*.pdf) and labels as cover_annualreviews.
"""

import re
from pathlib import Path

import pandas as pd
from docling.document_converter import DocumentConverter


def detect_annual_reviews_cover(text: str) -> bool:
    """Detect Annual Reviews cover page.

    Returns True if text contains Annual Reviews cover patterns.
    """
    patterns = [
        r"Downloaded from www\.annualreviews\.org",
        r"Annual Review",
        r"www\.annualreviews\.org",
        r"Access provided by",
        r"IP Address:",
    ]
    matches = sum(1 for p in patterns if re.search(p, text, re.I))
    return matches >= 2


def extract_annual_reviews_covers(pdf_dir: Path) -> list[dict]:
    """Extract Annual Reviews cover pages.

    Args:
        pdf_dir: Directory containing PDFs

    Returns:
        List of dicts with 'text', 'label', 'source' keys
    """
    converter = DocumentConverter()
    cover_samples = []

    stats = {"total_pdfs": 0, "with_cover": 0, "no_cover": 0, "total_paragraphs": 0, "errors": 0}

    print("Extracting Annual Reviews cover pages...")
    print("=" * 80)

    # Only process Annual Reviews PDFs
    annurev_pdfs = sorted(pdf_dir.glob("annurev-*.pdf"))

    if not annurev_pdfs:
        print(f"No Annual Reviews PDFs found in {pdf_dir}")
        return []

    print(f"Found {len(annurev_pdfs)} Annual Reviews PDFs\n")

    for pdf_path in annurev_pdfs:
        stats["total_pdfs"] += 1

        try:
            # Extract first page
            result = converter.convert(pdf_path)
            doc_md = result.document.export_to_markdown()

            # Get first page (roughly 100 lines)
            lines = doc_md.split("\n")
            first_page_text = "\n".join(lines[:100])

            # Detect Annual Reviews cover
            if detect_annual_reviews_cover(first_page_text):
                stats["with_cover"] += 1

                # Split into paragraphs
                paragraphs = [p.strip() for p in first_page_text.split("\n\n") if p.strip()]

                # Filter short paragraphs (< 20 chars)
                paragraphs = [p for p in paragraphs if len(p) >= 20]

                for para in paragraphs:
                    cover_samples.append(
                        {
                            "text": para,
                            "label": "cover_annualreviews",
                            "source": pdf_path.name,
                            "extraction_method": "pdf_first_page",
                        }
                    )
                    stats["total_paragraphs"] += 1

                print(f"✓ cover_annualreviews  {pdf_path.name}")
            else:
                stats["no_cover"] += 1
                print(f"✗ NO COVER DETECTED    {pdf_path.name}")

        except Exception as e:
            stats["errors"] += 1
            print(f"✗ ERROR: {pdf_path.name}: {e}")

    print("\n" + "=" * 80)
    print("EXTRACTION SUMMARY")
    print("=" * 80)
    print(f"Total PDFs processed:      {stats['total_pdfs']}")
    print(f"  With Annual Reviews cover: {stats['with_cover']}")
    print(f"  No cover detected:         {stats['no_cover']}")
    print(f"  Errors:                    {stats['errors']}")
    print(f"\nTotal cover paragraphs:    {stats['total_paragraphs']}")
    if stats["with_cover"] > 0:
        print(f"Average paragraphs/cover:  {stats['total_paragraphs'] / stats['with_cover']:.1f}")

    return cover_samples


def main():
    """Extract Annual Reviews covers and save."""
    base_dir = Path(__file__).parent
    pdf_dir = Path("/Users/donaldbraman/Documents/GitHub/12-factor-agents/test_corpus/pdfs")
    output_path = base_dir / "data" / "annual_reviews_covers.csv"

    if not pdf_dir.exists():
        print(f"Error: PDF directory not found: {pdf_dir}")
        return

    # Extract covers
    cover_samples = extract_annual_reviews_covers(pdf_dir)

    if not cover_samples:
        print("\nNo Annual Reviews cover pages found!")
        return

    # Save as CSV
    df = pd.DataFrame(cover_samples)
    output_path.parent.mkdir(exist_ok=True)
    df.to_csv(output_path, index=False)

    print(f"\n✓ Annual Reviews covers saved to: {output_path}")
    print(f"  {len(df)} paragraphs")

    # Show sample
    print("\n" + "=" * 80)
    print("SAMPLE PARAGRAPHS (first 3)")
    print("=" * 80)
    for i, row in df.head(3).iterrows():
        print(f"\n{row['source']}:")
        print(f"  {row['text'][:150]}...")


if __name__ == "__main__":
    main()
