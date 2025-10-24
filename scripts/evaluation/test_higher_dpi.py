#!/usr/bin/env python3
"""
Test higher DPI (600 DPI) vs standard 300 DPI for OCR quality.

Tests on worst-performing PDF: usc_law_review_listening_on_campus
"""

import json
import os
import time
from pathlib import Path

import fitz  # PyMuPDF
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, TesseractOcrOptions
from docling.document_converter import DocumentConverter, PdfFormatOption


def create_image_only_pdf(
    pdf_path: Path, output_path: Path, dpi: int, grayscale: bool = True
) -> None:
    """Create image-only PDF at specified DPI."""
    print(f"\n  Creating {dpi} DPI image-only PDF...")
    print(f"    Grayscale: {grayscale}")

    src_doc = fitz.open(str(pdf_path))
    img_doc = fitz.open()

    for i in range(len(src_doc)):
        page = src_doc[i]
        # Calculate matrix for desired DPI (72 is PDF's native DPI)
        mat = fitz.Matrix(dpi / 72, dpi / 72)

        if grayscale:
            pix = page.get_pixmap(matrix=mat, colorspace="gray")
        else:
            pix = page.get_pixmap(matrix=mat)

        img_page = img_doc.new_page(width=page.rect.width, height=page.rect.height)
        img_page.insert_image(img_page.rect, pixmap=pix)

    img_doc.save(str(output_path))
    img_doc.close()
    src_doc.close()

    file_size = output_path.stat().st_size / (1024 * 1024)  # MB
    print(f"    ✓ Created: {file_size:.1f} MB")


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
        "markdown_full_text": doc.document.export_to_markdown(),
        "page_count": len(doc.pages) if doc.pages else 0,
        "metadata": {
            "extraction_time_s": elapsed,
            "text_blocks": len([item.text for item in doc.document.texts])
            if doc.document.texts
            else 0,
            "tables": len(list(doc.document.tables)) if doc.document.tables else 0,
        },
    }

    with open(output_json, "w") as f:
        json.dump(extraction_data, f, indent=2)

    total_chars = sum(len(t) for t in all_text_blocks)
    print(f"    ✓ Extracted: {total_chars:,} chars, {len(all_text_blocks)} blocks")
    print(f"    Time: {elapsed:.1f}s")

    return extraction_data


def compare_extractions(extraction_a: dict, extraction_b: dict, label_a: str, label_b: str) -> None:
    """Compare two extractions."""
    texts_a = " ".join(extraction_a.get("texts", []))
    texts_b = " ".join(extraction_b.get("texts", []))

    chars_a = len(texts_a)
    chars_b = len(texts_b)

    blocks_a = len(extraction_a.get("texts", []))
    blocks_b = len(extraction_b.get("texts", []))

    print(f"\n{'=' * 80}")
    print(f"COMPARISON: {label_a} vs {label_b}")
    print(f"{'=' * 80}")
    print("Characters:")
    print(f"  {label_a}: {chars_a:,}")
    print(f"  {label_b}: {chars_b:,}")
    print(f"  Difference: {chars_b - chars_a:+,} ({100 * chars_b / chars_a:.1f}%)")

    print("\nBlocks:")
    print(f"  {label_a}: {blocks_a}")
    print(f"  {label_b}: {blocks_b}")
    print(f"  Difference: {blocks_b - blocks_a:+d}")


def main():
    """Test DPI variations on worst-performing PDF."""
    os.environ["TESSDATA_PREFIX"] = "/opt/homebrew/Cellar/tesseract/5.5.1/share/tessdata"

    # Test on worst performer
    pdf_name = "usc_law_review_listening_on_campus_academic_freedom_and_its_audiences"
    pdf_path = Path(f"data/v3_data/raw_pdf/{pdf_name}.pdf")

    output_dir = Path("results/dpi_test")
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("TESTING HIGHER DPI FOR OCR QUALITY")
    print("=" * 80)
    print(f"\nTest PDF: {pdf_name}")
    print("  (Worst performer: ocrmac got only 4.9% of ground truth)")
    print("\nTests:")
    print("  1. 300 DPI grayscale (current baseline)")
    print("  2. 600 DPI grayscale (high quality)")
    print("  3. 600 DPI color (maximum quality)")
    print("=" * 80)

    results = {}

    # Test 1: 300 DPI grayscale (baseline)
    print("\n[1/3] 300 DPI GRAYSCALE (baseline)")
    print("-" * 80)
    img_pdf_300 = output_dir / f"{pdf_name}_300dpi_gray.pdf"
    extraction_300 = output_dir / f"{pdf_name}_300dpi_gray_extraction.json"

    create_image_only_pdf(pdf_path, img_pdf_300, dpi=300, grayscale=True)
    results["300_dpi_gray"] = run_docling_tesseract(img_pdf_300, extraction_300)

    # Test 2: 600 DPI grayscale
    print("\n[2/3] 600 DPI GRAYSCALE (high quality)")
    print("-" * 80)
    img_pdf_600 = output_dir / f"{pdf_name}_600dpi_gray.pdf"
    extraction_600 = output_dir / f"{pdf_name}_600dpi_gray_extraction.json"

    create_image_only_pdf(pdf_path, img_pdf_600, dpi=600, grayscale=True)
    results["600_dpi_gray"] = run_docling_tesseract(img_pdf_600, extraction_600)

    # Test 3: 600 DPI color
    print("\n[3/3] 600 DPI COLOR (maximum quality)")
    print("-" * 80)
    img_pdf_600_color = output_dir / f"{pdf_name}_600dpi_color.pdf"
    extraction_600_color = output_dir / f"{pdf_name}_600dpi_color_extraction.json"

    create_image_only_pdf(pdf_path, img_pdf_600_color, dpi=600, grayscale=False)
    results["600_dpi_color"] = run_docling_tesseract(img_pdf_600_color, extraction_600_color)

    # Compare results
    compare_extractions(
        results["300_dpi_gray"], results["600_dpi_gray"], "300 DPI gray", "600 DPI gray"
    )
    compare_extractions(
        results["600_dpi_gray"], results["600_dpi_color"], "600 DPI gray", "600 DPI color"
    )
    compare_extractions(
        results["300_dpi_gray"], results["600_dpi_color"], "300 DPI gray", "600 DPI color"
    )

    # Save summary
    summary = {
        "pdf_name": pdf_name,
        "tests": {
            "300_dpi_gray": {
                "chars": len(" ".join(results["300_dpi_gray"].get("texts", []))),
                "blocks": len(results["300_dpi_gray"].get("texts", [])),
                "time_s": results["300_dpi_gray"]["metadata"]["extraction_time_s"],
            },
            "600_dpi_gray": {
                "chars": len(" ".join(results["600_dpi_gray"].get("texts", []))),
                "blocks": len(results["600_dpi_gray"].get("texts", [])),
                "time_s": results["600_dpi_gray"]["metadata"]["extraction_time_s"],
            },
            "600_dpi_color": {
                "chars": len(" ".join(results["600_dpi_color"].get("texts", []))),
                "blocks": len(results["600_dpi_color"].get("texts", [])),
                "time_s": results["600_dpi_color"]["metadata"]["extraction_time_s"],
            },
        },
    }

    summary_file = output_dir / "dpi_test_summary.json"
    with open(summary_file, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n{'=' * 80}")
    print("DPI TEST COMPLETE")
    print(f"{'=' * 80}")
    print(f"Results saved to: {output_dir}")


if __name__ == "__main__":
    main()
