#!/usr/bin/env python3
"""Test different docling extraction methods for JELS dual-column PDFs."""

from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    LayoutOptions,
    OcrMacOptions,
    PdfPipelineOptions,
)
from docling.document_converter import DocumentConverter, PdfFormatOption


def test_extraction_methods():
    """Test 3 extraction configurations on JELS PDF."""
    pdf_path = (
        Path.home()
        / "Downloads"
        / "J Empirical Legal Studies - 2025 - Yoon - In the Eye of the Beholder  How Lawyers Perceive Legal Ethical Problems.pdf"
    )

    if not pdf_path.exists():
        print(f"❌ PDF not found: {pdf_path}")
        return

    print("🔍 Testing extraction methods on JELS dual-column PDF")
    print(f"PDF: {pdf_path.name}\n")
    print("=" * 70)

    # Method 1: OCR only (current validation)
    print("\nMethod 1: OCR only (force_full_page_ocr=True)")
    print("-" * 70)

    ocr_options = OcrMacOptions(force_full_page_ocr=True)
    pipeline1 = PdfPipelineOptions(
        do_ocr=True,
        ocr_options=ocr_options,
        generate_page_images=True,
        images_scale=1.0,
    )

    converter1 = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline1)}
    )

    result1 = converter1.convert(str(pdf_path))

    paras1 = []
    for item, _level in result1.document.iterate_items():
        if hasattr(item, "text") and item.text and len(item.text.strip()) > 20:
            paras1.append(item.text.strip())

    print(f"Extracted {len(paras1)} paragraphs")
    print("\nFirst 3 paragraphs:")
    for i, para in enumerate(paras1[:3], 1):
        print(f"{i}. {para[:100]}...")

    # Method 2: LayoutOptions only (training pipeline)
    print("\n\nMethod 2: LayoutOptions only (training pipeline)")
    print("-" * 70)

    pipeline2 = PdfPipelineOptions(
        layout_options=LayoutOptions(),
        generate_parsed_pages=True,
        generate_page_images=True,
        images_scale=1.0,
    )

    converter2 = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline2)}
    )

    result2 = converter2.convert(str(pdf_path))

    paras2 = []
    for item, _level in result2.document.iterate_items():
        if hasattr(item, "text") and item.text and len(item.text.strip()) > 20:
            paras2.append(item.text.strip())

    print(f"Extracted {len(paras2)} paragraphs")
    print("\nFirst 3 paragraphs:")
    for i, para in enumerate(paras2[:3], 1):
        print(f"{i}. {para[:100]}...")

    # Method 3: LayoutOptions + OCR (combined)
    print("\n\nMethod 3: LayoutOptions + OCR (combined)")
    print("-" * 70)

    ocr_options3 = OcrMacOptions(force_full_page_ocr=True)
    pipeline3 = PdfPipelineOptions(
        layout_options=LayoutOptions(),
        do_ocr=True,
        ocr_options=ocr_options3,
        generate_parsed_pages=True,
        generate_page_images=True,
        images_scale=1.0,
    )

    converter3 = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline3)}
    )

    result3 = converter3.convert(str(pdf_path))

    paras3 = []
    for item, _level in result3.document.iterate_items():
        if hasattr(item, "text") and item.text and len(item.text.strip()) > 20:
            paras3.append(item.text.strip())

    print(f"Extracted {len(paras3)} paragraphs")
    print("\nFirst 3 paragraphs:")
    for i, para in enumerate(paras3[:3], 1):
        print(f"{i}. {para[:100]}...")

    # Summary
    print("\n\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Method 1 (OCR only):              {len(paras1)} paragraphs")
    print(f"Method 2 (LayoutOptions only):    {len(paras2)} paragraphs")
    print(f"Method 3 (LayoutOptions + OCR):   {len(paras3)} paragraphs")

    # Check for reading order differences
    print("\n📊 Reading order comparison (first paragraph):")
    print(f"Method 1 starts: {paras1[0][:80] if paras1 else 'N/A'}...")
    print(f"Method 2 starts: {paras2[0][:80] if paras2 else 'N/A'}...")
    print(f"Method 3 starts: {paras3[0][:80] if paras3 else 'N/A'}...")


if __name__ == "__main__":
    test_extraction_methods()
