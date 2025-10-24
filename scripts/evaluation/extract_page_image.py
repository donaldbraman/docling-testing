#!/usr/bin/env python3
"""
Extract a specific page from PDF as an image file.
"""

from pathlib import Path

import fitz  # PyMuPDF


def extract_page_as_image(pdf_path: Path, page_num: int, output_path: Path):
    """Extract a page as PNG image."""
    doc = fitz.open(str(pdf_path))

    if page_num < 1 or page_num > len(doc):
        print(f"Error: Page {page_num} out of range (1-{len(doc)})")
        return

    # Get page (0-indexed)
    page = doc[page_num - 1]

    # Render at high DPI
    mat = fitz.Matrix(300 / 72, 300 / 72)  # 300 DPI
    pix = page.get_pixmap(matrix=mat)

    # Save as PNG
    pix.save(str(output_path))

    doc.close()

    print(f"Saved page {page_num} to: {output_path}")
    print(f"Image size: {pix.width}x{pix.height}")
    print(f"Colorspace: {pix.colorspace}")


if __name__ == "__main__":
    pdf_path = Path(
        "results/ocr_pipeline_test/usc_law_review_in_the_name_of_accountability_image_only.pdf"
    )
    page_num = 4
    output_path = Path("results/page_4_extracted.png")

    extract_page_as_image(pdf_path, page_num, output_path)
