#!/usr/bin/env python3
"""
Test different Docling configurations to improve layout detection.

Tests various pipeline options on academic_limbo PDF to see if we can
capture the missing TOC and partial paragraph text.
"""

from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import OcrMacOptions, PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption


def test_config(name: str, pipeline_options: PdfPipelineOptions, pdf_path: Path):
    """Test a configuration and report results."""
    print(f"\n{'=' * 80}")
    print(f"Testing: {name}")
    print(f"{'=' * 80}")

    # Create converter with these options
    converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}
    )

    # Convert PDF
    doc = converter.convert(str(pdf_path))

    # Count items by type
    item_counts = {}
    for item in doc.document.texts:
        item_type = type(item).__name__
        item_counts[item_type] = item_counts.get(item_type, 0) + 1

    total_items = len(doc.document.texts)
    print(f"\n✓ Extracted {total_items} total items:")
    for item_type, count in sorted(item_counts.items()):
        print(f"    {item_type}: {count}")

    return total_items, item_counts


def main():
    """Test configurations on academic_limbo."""
    pdf_path = Path(
        "results/ocr_engine_comparison/academic_limbo__reforming_campus_speech_governance_for_students_image_only.pdf"
    )

    if not pdf_path.exists():
        print(f"Error: {pdf_path} not found")
        print("Run generate_ocr_overlay.py first to create image-only PDF")
        return 1

    results = {}

    # Config 1: Default (baseline)
    print("\n" + "=" * 80)
    print("Config 1: DEFAULT (baseline)")
    print("=" * 80)
    opts1 = PdfPipelineOptions()
    opts1.do_ocr = True
    opts1.ocr_options = OcrMacOptions()
    results["default"] = test_config("Default", opts1, pdf_path)

    # Config 2: Force full page OCR
    print("\n" + "=" * 80)
    print("Config 2: FORCE FULL PAGE OCR")
    print("=" * 80)
    opts2 = PdfPipelineOptions()
    opts2.do_ocr = True
    opts2.ocr_options = OcrMacOptions()
    opts2.ocr_options.force_full_page_ocr = True
    results["force_full_page_ocr"] = test_config("Force Full Page OCR", opts2, pdf_path)

    # Config 3: Lower bitmap threshold
    print("\n" + "=" * 80)
    print("Config 3: LOWER BITMAP THRESHOLD (0.01)")
    print("=" * 80)
    opts3 = PdfPipelineOptions()
    opts3.do_ocr = True
    opts3.ocr_options = OcrMacOptions()
    opts3.ocr_options.bitmap_area_threshold = 0.01
    results["low_threshold"] = test_config("Low Bitmap Threshold", opts3, pdf_path)

    # Config 4: Increase image scale
    print("\n" + "=" * 80)
    print("Config 4: INCREASE IMAGE SCALE (2.0x)")
    print("=" * 80)
    opts4 = PdfPipelineOptions()
    opts4.do_ocr = True
    opts4.ocr_options = OcrMacOptions()
    opts4.images_scale = 2.0
    results["high_scale"] = test_config("High Image Scale", opts4, pdf_path)

    # Config 5: Keep empty clusters
    print("\n" + "=" * 80)
    print("Config 5: KEEP EMPTY CLUSTERS")
    print("=" * 80)
    opts5 = PdfPipelineOptions()
    opts5.do_ocr = True
    opts5.ocr_options = OcrMacOptions()
    opts5.layout_options.keep_empty_clusters = True
    results["keep_empty"] = test_config("Keep Empty Clusters", opts5, pdf_path)

    # Config 6: Combined aggressive
    print("\n" + "=" * 80)
    print("Config 6: COMBINED AGGRESSIVE")
    print("=" * 80)
    opts6 = PdfPipelineOptions()
    opts6.do_ocr = True
    opts6.ocr_options = OcrMacOptions()
    opts6.ocr_options.force_full_page_ocr = True
    opts6.ocr_options.bitmap_area_threshold = 0.01
    opts6.images_scale = 2.0
    opts6.layout_options.keep_empty_clusters = True
    results["combined"] = test_config("Combined Aggressive", opts6, pdf_path)

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print("\nTotal items extracted by configuration:")
    baseline_count = results["default"][0]
    for config, (count, _) in results.items():
        diff = count - baseline_count
        diff_str = f"(+{diff})" if diff > 0 else f"({diff})" if diff < 0 else "(same)"
        print(f"  {config:25s}: {count:3d} items {diff_str}")

    print("\n✓ Test complete")
    return 0


if __name__ == "__main__":
    exit(main())
