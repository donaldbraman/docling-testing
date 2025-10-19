"""
Test baseline Docling extraction on sample PDFs.

Validates text layer extraction and fragmentation metrics
without requiring external OCR tools.
"""

import time
from pathlib import Path
from typing import Any

import pandas as pd
from docling.document_converter import DocumentConverter


def extract_and_analyze(pdf_path: Path) -> dict[str, Any]:
    """Extract PDF and analyze text fragmentation.

    Args:
        pdf_path: Path to PDF file

    Returns:
        Analysis dict with metrics
    """
    start = time.time()

    try:
        converter = DocumentConverter()
        doc = converter.convert(str(pdf_path))
        total_time = time.time() - start

        # Analyze text structure
        if doc.document and hasattr(doc.document, "texts"):
            text_items = doc.document.texts if doc.document.texts else []
            item_count = len(text_items)
        else:
            text_items = []
            item_count = 0

        pages = doc.pages if doc.pages else []
        page_count = len(pages)

        # Calculate fragmentation metrics
        items_per_page = item_count / page_count if page_count > 0 else 0

        return {
            "pdf": pdf_path.name,
            "success": True,
            "extraction_time_ms": total_time * 1000,
            "item_count": item_count,
            "page_count": page_count,
            "items_per_page": items_per_page,
            "text_sample": text_items[0] if text_items else "",
            "error": None,
        }
    except Exception as e:
        return {
            "pdf": pdf_path.name,
            "success": False,
            "extraction_time_ms": time.time() - start,
            "item_count": 0,
            "page_count": 0,
            "items_per_page": 0.0,
            "text_sample": "",
            "error": str(e),
        }


def main():
    """Test baseline extraction on sample PDFs."""
    pdf_dir = Path("data/v3_data/raw_pdf")

    if not pdf_dir.exists():
        print(f"Error: PDF directory not found: {pdf_dir}")
        return

    # Get sample PDFs
    pdf_paths = sorted(pdf_dir.glob("*.pdf"))[:5]

    if not pdf_paths:
        print(f"Error: No PDFs found in {pdf_dir}")
        return

    print(f"Testing baseline extraction on {len(pdf_paths)} PDFs\n")

    results = []
    for i, pdf_path in enumerate(pdf_paths, 1):
        print(f"[{i}/{len(pdf_paths)}] {pdf_path.name}... ", end="", flush=True)
        result = extract_and_analyze(pdf_path)

        if result["success"]:
            print(
                f"✓ {result['item_count']} items, "
                f"{result['items_per_page']:.1f} per page, "
                f"{result['extraction_time_ms']:.0f}ms"
            )
        else:
            print(f"✗ {result['error']}")

        results.append(result)

    # Summary
    df = pd.DataFrame(results)
    successful = df[df["success"]]

    print("\nBASELINE EXTRACTION SUMMARY")
    print("=" * 60)
    print(f"Success Rate: {len(successful)}/{len(results)}")
    print(f"Avg Extraction Time: {successful['extraction_time_ms'].mean():.0f}ms")
    print(f"Avg Items/Page: {successful['items_per_page'].mean():.1f}")
    print(f"Total Items: {successful['item_count'].sum()}")

    # Save results
    output_dir = Path("results/ocr_comparison")
    output_dir.mkdir(parents=True, exist_ok=True)

    df.to_csv(output_dir / "baseline_extraction_test.csv", index=False)
    print(f"\nResults saved to {output_dir / 'baseline_extraction_test.csv'}")


if __name__ == "__main__":
    main()
