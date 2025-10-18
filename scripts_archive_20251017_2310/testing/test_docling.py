#!/usr/bin/env python3
"""Test Docling extraction on law review articles."""

import time
from pathlib import Path

from docling.document_converter import DocumentConverter


def test_single_pdf(pdf_path: Path, output_dir: Path) -> dict:
    """
    Extract text from a single PDF using Docling.

    Returns:
        dict with metrics and metadata
    """
    print(f"\n{'=' * 80}")
    print(f"Processing: {pdf_path.name}")
    print(f"{'=' * 80}")

    start_time = time.time()

    # Initialize converter
    converter = DocumentConverter()

    # Convert PDF
    result = converter.convert(str(pdf_path))

    # Export to markdown
    markdown = result.document.export_to_markdown()

    elapsed = time.time() - start_time

    # Save markdown output
    output_path = output_dir / f"{pdf_path.stem}.md"
    output_path.write_text(markdown, encoding="utf-8")

    # Quick analysis
    metrics = {
        "filename": pdf_path.name,
        "elapsed_seconds": round(elapsed, 2),
        "output_length": len(markdown),
        "word_count": len(markdown.split()),
        "hyphen_linebreak_count": markdown.count("-\n"),
        "contains_footnote_marker": "footnote" in markdown.lower(),
        "paragraph_count": len([p for p in markdown.split("\n\n") if p.strip()]),
    }

    # Print metrics
    print("\n✅ Extraction complete!")
    print(f"   Time: {metrics['elapsed_seconds']}s")
    print(f"   Words: {metrics['word_count']:,}")
    print(f"   Hyphenation artifacts: {metrics['hyphen_linebreak_count']}")
    print(f"   Contains 'footnote': {metrics['contains_footnote_marker']}")
    print(f"   Output saved to: {output_path}")

    return metrics


def main():
    """Run tests on all PDFs in test corpus."""

    # Setup paths
    base_dir = Path(__file__).parent
    test_corpus = base_dir / "test_corpus" / "law_reviews"
    output_dir = base_dir / "results" / "docling"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Find all PDFs
    pdfs = sorted(test_corpus.glob("*.pdf"))

    if not pdfs:
        print("❌ No PDFs found in test_corpus/law_reviews/")
        return

    print("\n🔬 DOCLING EXTRACTION TEST")
    print(f"Found {len(pdfs)} test PDFs")

    # Process each PDF
    all_metrics = []
    for pdf_path in pdfs:
        try:
            metrics = test_single_pdf(pdf_path, output_dir)
            all_metrics.append(metrics)
        except Exception as e:
            print(f"❌ Error processing {pdf_path.name}: {e}")

    # Summary
    if all_metrics:
        print(f"\n{'=' * 80}")
        print("SUMMARY")
        print(f"{'=' * 80}")

        total_time = sum(m["elapsed_seconds"] for m in all_metrics)
        avg_time = total_time / len(all_metrics)
        total_words = sum(m["word_count"] for m in all_metrics)
        total_hyphens = sum(m["hyphen_linebreak_count"] for m in all_metrics)
        docs_with_footnotes = sum(1 for m in all_metrics if m["contains_footnote_marker"])

        print(f"Documents processed: {len(all_metrics)}")
        print(f"Total time: {total_time:.2f}s")
        print(f"Average time: {avg_time:.2f}s per document")
        print(f"Total words extracted: {total_words:,}")
        print(f"Total hyphenation artifacts: {total_hyphens}")
        print(f"Documents with 'footnote': {docs_with_footnotes}/{len(all_metrics)}")

        print(f"\n📁 Results saved to: {output_dir}")


if __name__ == "__main__":
    main()
