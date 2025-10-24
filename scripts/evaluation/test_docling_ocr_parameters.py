#!/usr/bin/env python3
"""
Test different Docling OCR parameters on the same document.
Compare completion rates to find optimal configuration.
"""

import json
import re
from pathlib import Path
from typing import Any

from docling.backend.ocr_backend import OcrBackend
from docling.datamodel.pipeline_options import OcrOptions, PdfPipelineOptions
from docling.document_converter import DocumentConverter


def normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    return re.sub(r"\s+", " ", text).strip().lower()


def extract_with_config(
    pdf_path: Path, config_name: str, pipeline_options: PdfPipelineOptions
) -> dict[str, Any]:
    """Extract text using specific Docling configuration."""
    print(f"\n{'=' * 80}")
    print(f"Testing: {config_name}")
    print(f"{'=' * 80}")

    converter = DocumentConverter()
    doc = converter.convert(str(pdf_path), pipeline_options=pipeline_options)

    # Collect all text
    all_texts = []
    if doc.document.texts:
        all_texts.extend([item.text for item in doc.document.texts])
    if doc.document.tables:
        for table in doc.document.tables:
            table_md = table.export_to_markdown(doc.document)
            if table_md:
                all_texts.append(table_md)

    # Search for the test paragraph
    search_text = "Given the growing importance of UE theory"
    search_normalized = normalize_text(search_text)
    found = False
    found_in_block = None

    for i, text in enumerate(all_texts):
        if search_normalized in normalize_text(text):
            found = True
            found_in_block = i
            break

    print(f"  Text blocks extracted: {len(all_texts)}")
    print(f"  Test paragraph: {'✓ FOUND' if found else '✗ NOT FOUND'}")
    if found:
        print(f"  Found in block: {found_in_block}")

    return {
        "config_name": config_name,
        "text_blocks": len(all_texts),
        "test_paragraph_found": found,
        "found_in_block": found_in_block,
        "all_texts": all_texts,
    }


def main():
    """Test different OCR configurations."""
    pdf_path = Path(
        "results/ocr_pipeline_test/usc_law_review_in_the_name_of_accountability_image_only.pdf"
    )
    output_dir = Path("results/ocr_parameter_tests")
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Testing document: {pdf_path.name}")
    print(f"Output directory: {output_dir}")

    # Test configurations
    configs = []

    # Config 1: Baseline (default ocrmac)
    configs.append({"name": "baseline_ocrmac", "options": PdfPipelineOptions()})

    # Config 2: Tesseract OCR
    try:
        configs.append(
            {
                "name": "tesseract_default",
                "options": PdfPipelineOptions(
                    do_ocr=True, ocr_options=OcrOptions(use_gpu=False, backend=OcrBackend.TESSERACT)
                ),
            }
        )
    except Exception as e:
        print(f"Warning: Could not configure Tesseract: {e}")

    # Config 3: EasyOCR
    try:
        configs.append(
            {
                "name": "easyocr_default",
                "options": PdfPipelineOptions(
                    do_ocr=True, ocr_options=OcrOptions(use_gpu=False, backend=OcrBackend.EASYOCR)
                ),
            }
        )
    except Exception as e:
        print(f"Warning: Could not configure EasyOCR: {e}")

    # Run all configurations
    results = []
    for config in configs:
        try:
            result = extract_with_config(pdf_path, config["name"], config["options"])
            results.append(result)

            # Save extraction
            extraction_path = output_dir / f"{config['name']}_extraction.json"
            with open(extraction_path, "w") as f:
                json.dump(
                    {
                        "texts": result["all_texts"],
                        "metadata": {
                            "config": config["name"],
                            "text_blocks": result["text_blocks"],
                            "test_paragraph_found": result["test_paragraph_found"],
                        },
                    },
                    f,
                    indent=2,
                    default=str,
                )
            print(f"  Saved to: {extraction_path}")

        except Exception as e:
            print(f"  ✗ ERROR: {e}")
            results.append({"config_name": config["name"], "error": str(e)})

    # Summary comparison
    print(f"\n{'=' * 80}")
    print("SUMMARY COMPARISON")
    print(f"{'=' * 80}")
    print(f"{'Configuration':<30} {'Text Blocks':<15} {'Test Para Found'}")
    print("-" * 80)

    for result in results:
        if "error" in result:
            print(f"{result['config_name']:<30} {'ERROR':<15} {'-'}")
        else:
            found_str = "✓ YES" if result["test_paragraph_found"] else "✗ NO"
            print(f"{result['config_name']:<30} {result['text_blocks']:<15} {found_str}")

    # Save summary
    summary_path = output_dir / "parameter_test_summary.json"
    with open(summary_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nSummary saved to: {summary_path}")


if __name__ == "__main__":
    main()
