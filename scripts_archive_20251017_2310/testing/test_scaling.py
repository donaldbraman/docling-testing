#!/usr/bin/env python3
"""Test different image scaling factors to find optimal quality/speed."""

import time
from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    LayoutOptions,
    PdfPipelineOptions,
    TableFormerMode,
)
from docling.document_converter import DocumentConverter, PdfFormatOption


def test_with_scaling(pdf_path: Path, scale: float, output_dir: Path) -> dict:
    """
    Test extraction with specific image scaling factor.

    Args:
        pdf_path: Path to PDF
        scale: Image scaling factor (1.0, 2.0, 3.0)
        output_dir: Where to save results
    """
    print(f"\n{'=' * 80}")
    print(f"TESTING: {pdf_path.name} with {scale}x scaling")
    print(f"{'=' * 80}")

    start_time = time.time()

    # Configure pipeline with Heron model + settings
    pipeline = PdfPipelineOptions(
        # Heron layout model (newest, most accurate)
        layout_options=LayoutOptions(),
        # Enable parsed pages for layout inspection
        generate_parsed_pages=True,
        generate_page_images=True,
        # Variable image scaling (TEST THIS)
        images_scale=scale,
        # Accurate table mode
        do_table_structure=True,
        table_structure_options=dict(
            mode=TableFormerMode.ACCURATE,
            do_cell_matching=False,
        ),
        # OCR (uses ocrmac on Mac)
        do_ocr=True,
    )

    # Create converter with pipeline options
    converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline)}
    )

    # Convert document
    result = converter.convert(str(pdf_path))
    doc = result.document

    elapsed = time.time() - start_time

    # Export markdown
    markdown = doc.export_to_markdown()

    # Save with scale suffix
    output_path = output_dir / f"{pdf_path.stem}_scale_{scale}x.md"
    output_path.write_text(markdown, encoding="utf-8")

    # Analyze parsed pages (if available)
    footnote_boxes = 0
    text_boxes = 0
    header_boxes = 0
    footer_boxes = 0

    if hasattr(result, "pages") and result.pages:
        for page in result.pages:
            if hasattr(page, "predictions") and page.predictions:
                for pred in page.predictions:
                    label = str(pred.label).lower() if hasattr(pred, "label") else ""
                    if "footnote" in label:
                        footnote_boxes += 1
                    elif "text" in label or "paragraph" in label:
                        text_boxes += 1
                    elif "header" in label:
                        header_boxes += 1
                    elif "footer" in label:
                        footer_boxes += 1

    # Quick metrics
    metrics = {
        "scale": scale,
        "elapsed_seconds": round(elapsed, 2),
        "output_length": len(markdown),
        "word_count": len(markdown.split()),
        "hyphen_linebreak_count": markdown.count("-\n"),
        "footnote_boxes_detected": footnote_boxes,
        "text_boxes_detected": text_boxes,
        "header_boxes_detected": header_boxes,
        "footer_boxes_detected": footer_boxes,
    }

    # Print results
    print("\n✅ Extraction complete!")
    print(f"   Time: {metrics['elapsed_seconds']}s")
    print(f"   Words: {metrics['word_count']:,}")
    print(f"   Hyphenation artifacts: {metrics['hyphen_linebreak_count']}")
    print("   Layout detection:")
    print(f"     - Footnote boxes: {footnote_boxes}")
    print(f"     - Text boxes: {text_boxes}")
    print(f"     - Header boxes: {header_boxes}")
    print(f"     - Footer boxes: {footer_boxes}")
    print(f"   Output saved to: {output_path}")

    return metrics


def main():
    """Test scaling factors on a single representative PDF."""

    base_dir = Path(__file__).parent
    test_corpus = base_dir / "test_corpus" / "law_reviews"
    output_dir = base_dir / "results" / "scaling_test"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Test on Jackson (largest, most complex)
    test_pdf = test_corpus / "Jackson_2014.pdf"

    if not test_pdf.exists():
        print(f"❌ Test PDF not found: {test_pdf}")
        return

    print("\n🔬 DOCLING SCALING TEST")
    print(f"Test document: {test_pdf.name}")
    print("M1 Pro with 32GB RAM\n")

    # Test three scaling factors
    scales = [1.0, 2.0, 3.0]
    all_metrics = []

    for scale in scales:
        try:
            metrics = test_with_scaling(test_pdf, scale, output_dir)
            all_metrics.append(metrics)
        except Exception as e:
            print(f"❌ Error with {scale}x: {e}")
            import traceback

            traceback.print_exc()

    # Summary comparison
    if all_metrics:
        print(f"\n{'=' * 80}")
        print("SCALING COMPARISON")
        print(f"{'=' * 80}\n")

        print(f"{'Scale':<8} {'Time (s)':<10} {'Words':<10} {'Hyphens':<10} {'Footnotes':<12}")
        print("-" * 80)
        for m in all_metrics:
            print(
                f"{m['scale']:.1f}x      "
                f"{m['elapsed_seconds']:<10.1f} "
                f"{m['word_count']:<10,} "
                f"{m['hyphen_linebreak_count']:<10} "
                f"{m['footnote_boxes_detected']:<12}"
            )

        print(f"\n📁 Results saved to: {output_dir}")
        print("\nRecommendation:")
        print("  - Compare markdown outputs manually")
        print("  - Check if higher scaling improves footnote detection")
        print("  - Balance quality vs processing time")


if __name__ == "__main__":
    main()
