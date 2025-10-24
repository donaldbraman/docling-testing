#!/usr/bin/env python3
"""
Test TRUE grayscale conversion and OCR on worst-performing PDF.

Previous bug: insert_image() was converting grayscale back to RGB!
Fix: Save pixmap as PNG, then insert the PNG file instead.
"""

import json
import os
import time
from pathlib import Path

import fitz  # PyMuPDF
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, TesseractOcrOptions
from docling.document_converter import DocumentConverter, PdfFormatOption


def create_true_grayscale_pdf(pdf_path: Path, output_path: Path, dpi: int) -> None:
    """Create TRUE grayscale image-only PDF."""
    print(f"\n  Creating TRUE grayscale {dpi} DPI PDF...")

    src_doc = fitz.open(str(pdf_path))
    img_doc = fitz.open()

    temp_dir = Path("results/temp_images")
    temp_dir.mkdir(parents=True, exist_ok=True)

    for i in range(len(src_doc)):
        page = src_doc[i]
        mat = fitz.Matrix(dpi / 72, dpi / 72)

        # Create grayscale pixmap
        pix = page.get_pixmap(matrix=mat, colorspace="gray")

        # Save as grayscale PNG (preserves colorspace)
        temp_png = temp_dir / f"page_{i}_gray.png"
        pix.save(str(temp_png))

        # Create new page and insert PNG
        img_page = img_doc.new_page(width=page.rect.width, height=page.rect.height)
        img_page.insert_image(img_page.rect, filename=str(temp_png))

        # Clean up temp file
        temp_png.unlink()

    img_doc.save(str(output_path))
    img_doc.close()
    src_doc.close()

    # Verify it's actually grayscale
    verify_doc = fitz.open(str(output_path))
    verify_pix = verify_doc[0].get_pixmap()
    is_gray = verify_pix.colorspace and "Gray" in str(verify_pix.colorspace)
    verify_doc.close()

    file_size = output_path.stat().st_size / (1024 * 1024)
    print(f"    ✓ Created: {file_size:.1f} MB")
    print(f"    Colorspace: {'GRAY' if is_gray else 'RGB (FAILED!)'}")

    return is_gray


def run_docling_tesseract(image_pdf: Path, output_json: Path) -> dict:
    """Run Docling with Tesseract OCR."""
    print("  Running Docling + Tesseract OCR...")
    start = time.time()

    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = True
    pipeline_options.ocr_options = TesseractOcrOptions()

    converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}
    )
    doc = converter.convert(str(image_pdf))

    elapsed = time.time() - start

    # Extract text
    all_text_blocks = []
    if doc.document.texts:
        all_text_blocks.extend([item.text for item in doc.document.texts])

    if doc.document.tables:
        for table in doc.document.tables:
            table_md = table.export_to_markdown(doc.document)
            if table_md:
                all_text_blocks.append(table_md)

    extraction_data = {
        "texts": all_text_blocks,
        "page_count": len(doc.pages) if doc.pages else 0,
        "metadata": {
            "extraction_time_s": elapsed,
            "text_blocks": len(all_text_blocks),
        },
    }

    with open(output_json, "w") as f:
        json.dump(extraction_data, f, indent=2)

    total_chars = sum(len(t) for t in all_text_blocks)
    print(f"    ✓ Extracted: {total_chars:,} chars, {len(all_text_blocks)} blocks")
    print(f"    Time: {elapsed:.1f}s")

    return extraction_data


def main():
    """Test TRUE grayscale conversion vs fake grayscale."""
    os.environ["TESSDATA_PREFIX"] = "/opt/homebrew/Cellar/tesseract/5.5.1/share/tessdata"

    pdf_name = "usc_law_review_listening_on_campus_academic_freedom_and_its_audiences"
    pdf_path = Path(f"data/v3_data/raw_pdf/{pdf_name}.pdf")

    output_dir = Path("results/grayscale_fix_test")
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("TESTING TRUE GRAYSCALE CONVERSION")
    print("=" * 80)
    print("\nProblem: Previous pipeline created RGB PDFs, not grayscale!")
    print(f"Test PDF: {pdf_name} (worst performer: 4.9% recall)")
    print("=" * 80)

    # Test 1: TRUE grayscale at 300 DPI
    print("\n[1/2] TRUE GRAYSCALE 300 DPI")
    print("-" * 80)
    true_gray_pdf = output_dir / f"{pdf_name}_true_gray_300dpi.pdf"
    true_gray_extraction = output_dir / f"{pdf_name}_true_gray_300dpi_extraction.json"

    is_gray = create_true_grayscale_pdf(pdf_path, true_gray_pdf, dpi=300)

    if not is_gray:
        print("  ⚠️  WARNING: Still RGB after conversion!")

    result_true_gray = run_docling_tesseract(true_gray_pdf, true_gray_extraction)

    # Test 2: TRUE grayscale at 600 DPI
    print("\n[2/2] TRUE GRAYSCALE 600 DPI")
    print("-" * 80)
    true_gray_600_pdf = output_dir / f"{pdf_name}_true_gray_600dpi.pdf"
    true_gray_600_extraction = output_dir / f"{pdf_name}_true_gray_600dpi_extraction.json"

    is_gray_600 = create_true_grayscale_pdf(pdf_path, true_gray_600_pdf, dpi=600)
    result_true_gray_600 = run_docling_tesseract(true_gray_600_pdf, true_gray_600_extraction)

    # Compare
    chars_300 = sum(len(t) for t in result_true_gray.get("texts", []))
    chars_600 = sum(len(t) for t in result_true_gray_600.get("texts", []))

    print(f"\n{'=' * 80}")
    print("RESULTS")
    print(f"{'=' * 80}")
    print(f"TRUE grayscale 300 DPI: {chars_300:,} chars")
    print(f"TRUE grayscale 600 DPI: {chars_600:,} chars")
    print(f"Difference: {chars_600 - chars_300:+,} chars ({100 * chars_600 / chars_300:.1f}%)")

    # Compare to baseline
    baseline_file = Path(
        "results/ocr_pipeline_evaluation/extractions/usc_law_review_listening_on_campus_academic_freedom_and_its_audiences_baseline_extraction.json"
    )
    if baseline_file.exists():
        with open(baseline_file) as f:
            baseline_data = json.load(f)
        baseline_chars = len(" ".join(baseline_data.get("texts", [])))

        print("\nComparison to ocrmac baseline:")
        print(f"  Baseline (ocrmac): {baseline_chars:,} chars")
        print(f"  TRUE gray 300 DPI: {100 * chars_300 / baseline_chars:.1f}% coverage")
        print(f"  TRUE gray 600 DPI: {100 * chars_600 / baseline_chars:.1f}% coverage")


if __name__ == "__main__":
    main()
