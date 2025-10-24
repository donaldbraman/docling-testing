#!/usr/bin/env python3
"""
Test ocrmac with detail=False vs detail=True to see output differences.

Usage:
    uv run python scripts/evaluation/test_ocrmac_detail_false.py --pdf political_mootness
"""

import argparse
from pathlib import Path

from ocrmac import ocrmac
from pdf2image import convert_from_path


def test_detail_modes(image_pdf: Path):
    """Test ocrmac with detail=True vs detail=False."""

    # Convert first page only
    images = convert_from_path(str(image_pdf), dpi=600, grayscale=True, first_page=1, last_page=1)
    img = images[0]

    # Save temp image
    temp_img = "/tmp/test_ocr.png"
    img.save(temp_img)

    print(f"\n{'=' * 60}")
    print("Testing detail=True (default)")
    print(f"{'=' * 60}\n")

    # Test with detail=True
    ocr_true = ocrmac.OCR(
        temp_img, recognition_level="accurate", language_preference=["en-US"], detail=True
    )
    result_true = ocr_true.recognize()

    print(f"Type: {type(result_true)}")
    print(f"Length: {len(result_true)}")
    print("\nFirst 3 items:")
    for i, item in enumerate(result_true[:3]):
        print(f"\n  Item {i}:")
        print(f"    Type: {type(item)}")
        print(f"    Length: {len(item)}")
        print(f"    Content: {item}")

    print(f"\n{'=' * 60}")
    print("Testing detail=False")
    print(f"{'=' * 60}\n")

    # Test with detail=False
    ocr_false = ocrmac.OCR(
        temp_img, recognition_level="accurate", language_preference=["en-US"], detail=False
    )
    result_false = ocr_false.recognize()

    print(f"Type: {type(result_false)}")
    print(f"Length: {len(result_false)}")
    print("\nFirst 3 items:")
    for i, item in enumerate(result_false[:3]):
        print(f"\n  Item {i}:")
        print(f"    Type: {type(item)}")
        if isinstance(item, str):
            print(f"    Length: {len(item)} chars")
            print(f"    Preview: {item[:100]}...")
        else:
            print(f"    Content: {item}")

    # Check for line breaks
    if result_false and isinstance(result_false[0], str):
        text = result_false[0]
        print(f"\n{'=' * 60}")
        print("Line Break Analysis")
        print(f"{'=' * 60}\n")
        print(f"Contains \\n: {chr(10) in text}")
        print(f"Contains \\r: {chr(13) in text}")
        print(f"Line count (split by \\n): {len(text.split(chr(10)))}")
        print("\nFirst 500 chars with visible newlines:")
        print(repr(text[:500]))


def main():
    parser = argparse.ArgumentParser(description="Test ocrmac detail modes")
    parser.add_argument("--pdf", required=True, help="PDF name (without .pdf extension)")
    args = parser.parse_args()

    # Use existing image-only PDF
    image_pdf = Path(f"results/text_block_extraction/{args.pdf}_image_only_600dpi.pdf")

    if not image_pdf.exists():
        # Try ocr_comparison directory
        from datetime import date

        today = date.today().strftime("%Y%m%d")
        image_pdf = Path(
            f"results/ocr_comparison/{today}/{args.pdf}_600dpi/{args.pdf}_image_only_600dpi.pdf"
        )

    if not image_pdf.exists():
        print("Error: Image-only PDF not found")
        print(f"Run: uv run python scripts/corpus_building/extract_with_ocr.py --pdf {args.pdf}")
        return

    test_detail_modes(image_pdf)


if __name__ == "__main__":
    main()
