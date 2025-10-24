#!/usr/bin/env python3
"""
Compare ocrmac with and without language_preference parameter.

Usage:
    uv run python scripts/evaluation/compare_ocrmac_language.py --pdf political_mootness --dpi 300
"""

import argparse
import difflib
import json
import time
from datetime import date
from pathlib import Path


def normalize_text_for_comparison(text: str) -> str:
    """Normalize text for fair OCR comparison."""
    import re
    import unicodedata

    # Normalize smart quotes and dashes
    text = text.replace("\u2018", "'").replace("\u2019", "'")  # ' ' → '
    text = text.replace("\u201c", '"').replace("\u201d", '"')  # " " → "
    text = text.replace("\u2014", "-").replace("\u2013", "-")  # — – → -

    # Remove control characters
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]", "", text)

    # Keep only allowed characters
    allowed_chars = []
    for char in text:
        if char.isascii() and (char.isalnum() or char in " .,!?:;'\"-()[]/&\n\t") or char in "§¶":
            allowed_chars.append(char)
        elif unicodedata.category(char).startswith("L"):
            try:
                decomposed = unicodedata.normalize("NFD", char)
                if decomposed[0].isascii():
                    allowed_chars.append(char)
            except:
                pass

    text = "".join(allowed_chars)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def create_image_only_pdf(pdf_path: Path, output_dir: Path, dpi: int = 300) -> Path:
    """Create greyscale image-only PDF."""
    import fitz

    output_path = output_dir / f"{pdf_path.stem}_image_only_{dpi}dpi.pdf"

    if output_path.exists():
        print(f"  Using cached image-only PDF: {output_path.name}")
        return output_path

    print(f"  Creating greyscale image-only PDF at {dpi} DPI...")

    src_doc = fitz.open(str(pdf_path))
    img_doc = fitz.open()

    for i in range(min(3, len(src_doc))):
        page = src_doc[i]
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat, colorspace=fitz.csGRAY)
        img_page = img_doc.new_page(width=page.rect.width, height=page.rect.height)
        img_page.insert_image(img_page.rect, pixmap=pix)

    img_doc.save(str(output_path))
    img_doc.close()
    src_doc.close()

    print(f"  ✓ Created: {output_path.name}")
    return output_path


def ocr_with_ocrmac(image_pdf: Path, language_preference=None) -> dict:
    """Run ocrmac OCR with optional language preference."""
    try:
        from ocrmac import ocrmac
        from pdf2image import convert_from_path
    except ImportError as e:
        return {"error": f"Missing dependency: {e}"}

    lang_label = "en-US" if language_preference else "auto"
    print(f"\n[ocrmac - language: {lang_label}]")
    print("  Running OCR with Apple Neural Engine...")

    start = time.time()

    try:
        images = convert_from_path(str(image_pdf), dpi=600, grayscale=True)

        all_text = []
        for i, img in enumerate(images):
            print(f"    Page {i + 1}/{len(images)}...")

            temp_img = f"/tmp/ocr_page_{i}.png"
            img.save(temp_img)

            # Run OCR with language preference
            if language_preference:
                annotations = ocrmac.OCR(
                    temp_img, recognition_level="accurate", language_preference=language_preference
                ).recognize()
            else:
                annotations = ocrmac.OCR(temp_img, recognition_level="accurate").recognize()

            page_text = " ".join([ann[0] for ann in annotations])
            all_text.append(page_text)

        combined_text = "\n\n".join(all_text)
        normalized_text = normalize_text_for_comparison(combined_text)

        elapsed = time.time() - start

        print(f"  ✓ Completed in {elapsed:.1f}s")
        print(f"  ✓ Chars extracted: {len(normalized_text):,}")

        return {
            "language": lang_label,
            "raw_text": combined_text,
            "normalized_text": normalized_text,
            "pages_processed": len(images),
            "time_seconds": elapsed,
            "chars_extracted": len(normalized_text),
        }

    except Exception as e:
        return {"error": str(e)}


def generate_html_diff(text1: str, text2: str, label1: str, label2: str, output_path: Path):
    """Generate HTML diff visualization between two texts."""
    lines1 = text1.splitlines()
    lines2 = text2.splitlines()

    differ = difflib.HtmlDiff(wrapcolumn=80)
    html = differ.make_file(
        lines1,
        lines2,
        fromdesc=label1,
        todesc=label2,
        context=True,
        numlines=3,
    )

    with open(output_path, "w") as f:
        f.write(html)

    print(f"\n  ✓ Diff saved: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Compare ocrmac with/without language preference")
    parser.add_argument("--pdf", required=True, help="PDF name (without .pdf extension)")
    parser.add_argument(
        "--dpi", type=int, default=300, help="DPI for image rendering (default: 300)"
    )
    args = parser.parse_args()

    pdf_path = Path(f"data/v3_data/raw_pdf/{args.pdf}.pdf")
    if not pdf_path.exists():
        print(f"Error: PDF not found: {pdf_path}")
        return

    today = date.today().strftime("%Y%m%d")
    test_dir = Path(f"results/ocr_comparison/{today}/{args.pdf}_{args.dpi}dpi_language_test")
    test_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'=' * 60}")
    print("ocrmac Language Preference Test")
    print(f"{'=' * 60}")
    print(f"PDF: {args.pdf}")
    print(f"DPI: {args.dpi}")
    print()

    # Create image-only PDF
    print(f"[Stage 1] Creating image-only PDF at {args.dpi} DPI...")
    image_pdf = create_image_only_pdf(pdf_path, test_dir, args.dpi)

    # Run OCR without language preference
    result_auto = ocr_with_ocrmac(image_pdf, language_preference=None)

    # Run OCR with English language preference
    result_en = ocr_with_ocrmac(image_pdf, language_preference=["en-US"])

    if "error" in result_auto or "error" in result_en:
        print("\nError running OCR:")
        if "error" in result_auto:
            print(f"  Auto: {result_auto['error']}")
        if "error" in result_en:
            print(f"  English: {result_en['error']}")
        return

    # Generate diff
    diff_dir = test_dir / "diffs"
    diff_dir.mkdir(exist_ok=True)

    diff_file = diff_dir / "auto_vs_english.html"

    print(f"\n{'=' * 60}")
    print("Generating Diff")
    print(f"{'=' * 60}")

    generate_html_diff(
        result_auto["normalized_text"],
        result_en["normalized_text"],
        f"Auto language ({result_auto['chars_extracted']:,} chars)",
        f"English preference ({result_en['chars_extracted']:,} chars)",
        diff_file,
    )

    # Save results
    results = {
        "pdf": args.pdf,
        "dpi": args.dpi,
        "auto_language": result_auto,
        "english_preference": result_en,
    }

    output_file = test_dir / "comparison.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n{'=' * 60}")
    print("Summary")
    print(f"{'=' * 60}")
    print(
        f"Auto language:      {result_auto['chars_extracted']:,} chars in {result_auto['time_seconds']:.1f}s"
    )
    print(
        f"English preference: {result_en['chars_extracted']:,} chars in {result_en['time_seconds']:.1f}s"
    )
    diff = result_en["chars_extracted"] - result_auto["chars_extracted"]
    pct = (diff / result_auto["chars_extracted"] * 100) if result_auto["chars_extracted"] > 0 else 0
    print(f"Difference:         {diff:+,} chars ({pct:+.1f}%)")
    print(f"\nResults saved to: {output_file}")
    print(f"Diff saved to: {diff_file}")


if __name__ == "__main__":
    main()
