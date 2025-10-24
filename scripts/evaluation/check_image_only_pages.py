#!/usr/bin/env python3
"""
Check which pages in the image-only PDF are black/corrupted.
"""

from pathlib import Path

import fitz  # PyMuPDF


def check_page_content(pdf_path: Path):
    """Check each page to see if it has visible content."""
    doc = fitz.open(str(pdf_path))

    print(f"Checking: {pdf_path.name}")
    print(f"Total pages: {len(doc)}\n")

    black_pages = []
    ok_pages = []

    for page_num in range(len(doc)):
        page = doc[page_num]

        # Get the page as an image
        pix = page.get_pixmap()

        # Check if page is mostly black by sampling pixels
        # Sample from different areas
        samples = []
        width, height = pix.width, pix.height

        # Sample 9 points across the page
        for x_frac in [0.25, 0.5, 0.75]:
            for y_frac in [0.25, 0.5, 0.75]:
                x = int(width * x_frac)
                y = int(height * y_frac)

                # Get pixel color (returns (r, g, b) tuple)
                pixel = pix.pixel(x, y)
                samples.append(pixel)

        # Calculate average brightness
        avg_brightness = sum(sum(pixel) for pixel in samples) / (len(samples) * 3)

        # If average brightness is very low, page is likely black
        is_black = avg_brightness < 10  # threshold of 10 out of 255

        if is_black:
            black_pages.append(page_num + 1)
            print(f"Page {page_num + 1}: ✗ BLACK (avg brightness: {avg_brightness:.1f})")
        else:
            ok_pages.append(page_num + 1)
            print(f"Page {page_num + 1}: ✓ OK (avg brightness: {avg_brightness:.1f})")

    doc.close()

    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print(f"{'=' * 60}")
    print(f"Total pages: {len(doc)}")
    print(f"OK pages: {len(ok_pages)}")
    print(f"Black pages: {len(black_pages)}")

    if black_pages:
        print(f"\nBlack page numbers: {black_pages}")

    return black_pages


if __name__ == "__main__":
    pdf_path = Path(
        "results/ocr_pipeline_test/usc_law_review_in_the_name_of_accountability_image_only.pdf"
    )
    check_page_content(pdf_path)
