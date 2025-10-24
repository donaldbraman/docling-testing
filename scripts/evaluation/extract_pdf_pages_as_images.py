#!/usr/bin/env python3
"""Extract specific PDF pages as high-resolution PNG images for inspection."""

from pathlib import Path

import fitz  # PyMuPDF


def extract_pages(pdf_path: Path, pages: list[int], output_dir: Path, dpi: int = 150):
    """
    Extract specific pages as PNG images.

    Args:
        pdf_path: Path to PDF file
        pages: List of page numbers (1-indexed)
        output_dir: Directory to save images
        dpi: Resolution for output images
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    pdf_name = pdf_path.stem
    doc = fitz.open(pdf_path)

    zoom = dpi / 72  # PDF is 72 DPI by default
    mat = fitz.Matrix(zoom, zoom)

    for page_num in pages:
        page_idx = page_num - 1  # Convert to 0-indexed

        if page_idx < 0 or page_idx >= len(doc):
            print(f"  Warning: Page {page_num} out of range (PDF has {len(doc)} pages)")
            continue

        page = doc[page_idx]
        pix = page.get_pixmap(matrix=mat)

        output_path = output_dir / f"{pdf_name}_page{page_num}.png"
        pix.save(output_path)

        print(f"  Saved page {page_num}: {output_path} ({pix.width}x{pix.height})")

    doc.close()


def main():
    """Extract pages 1 and 3 from bu_law_review_learning_from_history overlay."""
    pdf_path = Path(
        "results/ocr_engine_comparison/overlays/bu_law_review_learning_from_history_ocrmac_overlay.pdf"
    )
    output_dir = Path("results/ocr_engine_comparison/page_images")

    print(f"Extracting pages from: {pdf_path.name}")
    extract_pages(pdf_path, pages=[1, 3], output_dir=output_dir, dpi=150)
    print(f"\nImages saved to: {output_dir}")


if __name__ == "__main__":
    main()
