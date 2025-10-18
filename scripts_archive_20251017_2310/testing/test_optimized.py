#!/usr/bin/env python3
"""Test Docling with optimized configuration for Jackson_2014.pdf."""

import time
from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    LayoutOptions,
    PdfPipelineOptions,
    TableFormerMode,
)
from docling.document_converter import DocumentConverter, PdfFormatOption


def test_optimized_config(pdf_path: Path, output_dir: Path) -> dict:
    """
    Test extraction with optimized configuration.

    Configuration based on:
    - Jackson_2014.pdf: Complex two-column academic layout
    - Tables, figures, footnotes
    - M1 Pro MacBook, 32GB RAM, MPS acceleration
    """
    print(f"\n{'=' * 80}")
    print(f"OPTIMIZED CONFIGURATION TEST: {pdf_path.name}")
    print(f"{'=' * 80}\n")

    start_time = time.time()

    # Create layout options with Heron-101 model
    layout_opts = LayoutOptions()
    layout_opts.model_spec = "heron-101"  # Force specific Heron model
    layout_opts.single_column_fallback = True  # Prevent footnote merging

    # Configure pipeline with OPTIMIZED settings
    pipeline = PdfPipelineOptions(
        # Heron-101 model (best for multi-column PDFs)
        layout_options=layout_opts,
        # Enable parsed layout artifacts - CRITICAL
        generate_parsed_pages=True,
        generate_page_images=True,
        # Scale rendering resolution (2x recommended)
        images_scale=2.0,
        # Table and figure detection
        do_table_structure=True,
        table_structure_options=dict(
            mode=TableFormerMode.ACCURATE,
            do_cell_matching=False,
        ),
        # OCR for embedded figures
        do_ocr=True,
    )

    # Create converter with pipeline options
    converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline)}
    )

    # Convert document
    print("Converting document with optimized settings...")
    result = converter.convert(str(pdf_path))
    doc = result.document

    elapsed = time.time() - start_time

    # Export markdown
    markdown = doc.export_to_markdown()

    # Save output
    output_path = output_dir / f"{pdf_path.stem}_optimized.md"
    output_path.write_text(markdown, encoding="utf-8")

    # Analyze parsed pages - DETAILED INSPECTION
    print(f"\n{'=' * 80}")
    print("LAYOUT DETECTION ANALYSIS")
    print(f"{'=' * 80}\n")

    label_counts = {
        "header": 0,
        "footer": 0,
        "body": 0,
        "text": 0,
        "paragraph": 0,
        "caption": 0,
        "table": 0,
        "figure": 0,
        "footnote": 0,
        "title": 0,
        "section-header": 0,
        "other": 0,
    }

    total_boxes = 0

    if hasattr(result, "pages") and result.pages:
        print(f"✅ Found {len(result.pages)} parsed pages\n")

        for page_idx, page in enumerate(result.pages):
            page_boxes = 0

            # Check if page has predictions
            if hasattr(page, "predictions") and page.predictions:
                pred_obj = page.predictions

                # Try to iterate through predictions
                try:
                    # Check if it has a layout property
                    if hasattr(pred_obj, "layout"):
                        layout_items = pred_obj.layout
                        if hasattr(layout_items, "__iter__"):
                            for item in layout_items:
                                page_boxes += 1
                                total_boxes += 1

                                # Get label
                                label = None
                                for attr in ["label", "class_name", "type", "category"]:
                                    if hasattr(item, attr):
                                        label = str(getattr(item, attr)).lower()
                                        break

                                # Count by label
                                if label:
                                    matched = False
                                    for key in label_counts:
                                        if key in label:
                                            label_counts[key] += 1
                                            matched = True
                                            break
                                    if not matched:
                                        label_counts["other"] += 1
                except Exception as e:
                    print(f"  ❌ Page {page_idx + 1}: Error accessing predictions: {e}")

            if page_boxes > 0:
                print(f"  Page {page_idx + 1}: {page_boxes} boxes detected")

        print(f"\n{'=' * 80}")
        print("LABEL DISTRIBUTION")
        print(f"{'=' * 80}\n")

        for label, count in sorted(label_counts.items(), key=lambda x: -x[1]):
            if count > 0:
                print(f"  {label:20} : {count:>4} boxes")

        print(f"\n  TOTAL BOXES: {total_boxes}")

    else:
        print("❌ No parsed pages found!")

    # Quick metrics
    metrics = {
        "elapsed_seconds": round(elapsed, 2),
        "output_length": len(markdown),
        "word_count": len(markdown.split()),
        "hyphen_linebreak_count": markdown.count("-\n"),
        "total_boxes": total_boxes,
        "label_counts": label_counts,
    }

    # Print results
    print(f"\n{'=' * 80}")
    print("EXTRACTION RESULTS")
    print(f"{'=' * 80}\n")
    print(f"   Time: {metrics['elapsed_seconds']}s ({metrics['elapsed_seconds'] / 60:.1f} min)")
    print(f"   Words: {metrics['word_count']:,}")
    print(f"   Hyphenation artifacts: {metrics['hyphen_linebreak_count']}")
    print(f"   Output saved to: {output_path}")

    return metrics


def main():
    """Test optimized configuration on Jackson PDF."""

    base_dir = Path(__file__).parent
    test_corpus = base_dir / "test_corpus" / "law_reviews"
    output_dir = base_dir / "results" / "optimized_test"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Test on Jackson (largest, most complex)
    test_pdf = test_corpus / "Jackson_2014.pdf"

    if not test_pdf.exists():
        print(f"❌ Test PDF not found: {test_pdf}")
        return

    print("\n🔬 DOCLING OPTIMIZED CONFIGURATION TEST")
    print(f"Test document: {test_pdf.name}")
    print("Hardware: M1 Pro with 32GB RAM")
    print("Configuration:")
    print("  - Heron-101 model")
    print("  - 2x image scaling")
    print("  - Single-column fallback enabled")
    print("  - Full layout diagnostics")
    print()

    try:
        metrics = test_optimized_config(test_pdf, output_dir)

        print(f"\n{'=' * 80}")
        print("SUMMARY")
        print(f"{'=' * 80}\n")

        if metrics["total_boxes"] == 0:
            print("⚠️  WARNING: No bounding boxes detected!")
            print("   This may indicate:")
            print("   - Predictions not being accessed correctly")
            print("   - Configuration issue")
            print("   - Model not detecting layout elements")
        else:
            print(f"✅ Successfully detected {metrics['total_boxes']} layout elements")
            print(f"\n   Footnotes: {metrics['label_counts']['footnote']}")
            print(
                f"   Body/Text: {metrics['label_counts']['body'] + metrics['label_counts']['text']}"
            )
            print(f"   Tables: {metrics['label_counts']['table']}")
            print(f"   Figures: {metrics['label_counts']['figure']}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
