#!/usr/bin/env python3
"""
Run full corpus through: Grayscale Image-only PDF → Docling + Tesseract OCR pipeline.
After each PDF, compare with existing ocrmac baseline extraction and report differences.

Usage:
    uv run python scripts/evaluation/run_corpus_tesseract_with_comparison.py

    # Or in background:
    nohup uv run python scripts/evaluation/run_corpus_tesseract_with_comparison.py > corpus_tesseract_comparison.log 2>&1 &
"""

import csv
import json
import logging
import os
import re
import time
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    return re.sub(r"\s+", " ", text).strip().lower()


def compare_extractions(tesseract_path: Path, baseline_path: Path, comparison_dir: Path) -> dict:
    """Compare Tesseract extraction with ocrmac baseline.

    Args:
        tesseract_path: Path to Tesseract extraction JSON
        baseline_path: Path to baseline (ocrmac) extraction JSON
        comparison_dir: Directory to save comparison report

    Returns:
        Comparison results dict
    """
    logger.info(f"\n{'=' * 80}")
    logger.info("COMPARING EXTRACTIONS")
    logger.info(f"{'=' * 80}")
    logger.info(f"Tesseract: {tesseract_path.name}")
    logger.info(f"Baseline:  {baseline_path.name}")

    # Load extractions
    with open(tesseract_path) as f:
        tesseract_data = json.load(f)

    with open(baseline_path) as f:
        baseline_data = json.load(f)

    # Extract text blocks (both should now be clean text strings)
    tesseract_texts = tesseract_data.get("texts", [])
    baseline_texts = baseline_data.get("texts", [])

    # Combine all text for coverage comparison
    tesseract_full_text = normalize_text(" ".join(tesseract_texts))
    baseline_full_text = normalize_text(" ".join(baseline_texts))

    # Calculate metrics
    tesseract_char_count = len(tesseract_full_text)
    baseline_char_count = len(baseline_full_text)

    # Calculate coverage (what % of baseline is in Tesseract)
    coverage = tesseract_char_count / baseline_char_count * 100 if baseline_char_count > 0 else 0.0

    # Find unique content
    tesseract_words = set(tesseract_full_text.split())
    baseline_words = set(baseline_full_text.split())

    only_in_tesseract = tesseract_words - baseline_words
    only_in_baseline = baseline_words - tesseract_words

    comparison_result = {
        "tesseract_blocks": len(tesseract_texts),
        "baseline_blocks": len(baseline_texts),
        "block_diff": len(tesseract_texts) - len(baseline_texts),
        "tesseract_chars": tesseract_char_count,
        "baseline_chars": baseline_char_count,
        "char_diff": tesseract_char_count - baseline_char_count,
        "coverage_pct": coverage,
        "unique_tesseract_words": len(only_in_tesseract),
        "unique_baseline_words": len(only_in_baseline),
        "tesseract_pages": tesseract_data.get("page_count", 0),
        "baseline_pages": baseline_data.get("page_count", 0),
    }

    # Log comparison
    logger.info("\nText Blocks:")
    logger.info(f"  Tesseract: {comparison_result['tesseract_blocks']}")
    logger.info(f"  Baseline:  {comparison_result['baseline_blocks']}")
    logger.info(f"  Difference: {comparison_result['block_diff']:+d}")

    logger.info("\nCharacter Count:")
    logger.info(f"  Tesseract: {comparison_result['tesseract_chars']:,}")
    logger.info(f"  Baseline:  {comparison_result['baseline_chars']:,}")
    logger.info(f"  Difference: {comparison_result['char_diff']:+,}")

    logger.info("\nCoverage:")
    logger.info(f"  Tesseract contains {coverage:.1f}% of baseline content")

    if coverage < 90:
        logger.warning("  ⚠️  Low coverage! Tesseract may be missing significant content")
    elif coverage > 110:
        logger.info(f"  ✓ Tesseract extracted {coverage - 100:.1f}% MORE content than baseline")
    else:
        logger.info("  ✓ Coverage looks good")

    logger.info("\nUnique Words:")
    logger.info(f"  Only in Tesseract: {comparison_result['unique_tesseract_words']}")
    logger.info(f"  Only in Baseline:  {comparison_result['unique_baseline_words']}")

    # Show sample of differences if significant
    if comparison_result["unique_baseline_words"] > 50:
        sample_missing = list(only_in_baseline)[:10]
        logger.warning(f"\n⚠️  Sample words missing from Tesseract: {', '.join(sample_missing)}")

    if comparison_result["unique_tesseract_words"] > 50:
        sample_extra = list(only_in_tesseract)[:10]
        logger.info(f"\n✓ Sample extra words in Tesseract: {', '.join(sample_extra)}")

    # Save detailed comparison report
    pdf_name = tesseract_path.stem.replace("_tesseract_extraction", "")
    comparison_file = comparison_dir / f"{pdf_name}_comparison.json"

    detailed_comparison = {
        "pdf_name": pdf_name,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "files": {"tesseract": str(tesseract_path), "baseline": str(baseline_path)},
        "metrics": comparison_result,
        "samples": {
            "unique_in_tesseract": list(only_in_tesseract)[:50],
            "unique_in_baseline": list(only_in_baseline)[:50],
        },
    }

    with open(comparison_file, "w") as f:
        json.dump(detailed_comparison, f, indent=2)

    logger.info(f"\n✓ Saved comparison report: {comparison_file.name}")

    return comparison_result


def create_grayscale_image_only_pdf(pdf_path: Path, output_dir: Path) -> Path:
    """Create grayscale image-only PDF by rasterizing all pages."""
    import fitz  # PyMuPDF

    output_path = output_dir / f"{pdf_path.stem}_grayscale_image_only.pdf"

    if output_path.exists():
        logger.info(f"  Using cached grayscale PDF: {output_path.name}")
        return output_path

    logger.info(f"  Creating grayscale image-only PDF from: {pdf_path.name}")

    src_doc = fitz.open(str(pdf_path))
    total_pages = len(src_doc)
    img_doc = fitz.open()

    for i in range(total_pages):
        page = src_doc[i]
        mat = fitz.Matrix(300 / 72, 300 / 72)
        pix = page.get_pixmap(matrix=mat, colorspace="gray")
        img_page = img_doc.new_page(width=page.rect.width, height=page.rect.height)
        img_page.insert_image(img_page.rect, pixmap=pix)

    img_doc.save(str(output_path))
    img_doc.close()
    src_doc.close()

    logger.info(f"  ✓ Created grayscale image-only PDF: {total_pages} pages")
    return output_path


def run_docling_tesseract_ocr(image_pdf: Path, output_dir: Path) -> Path:
    """Run Docling with Tesseract OCR and extract text."""
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions, TesseractOcrOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption

    logger.info("  Running Docling with Tesseract OCR...")
    start = time.time()

    try:
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = True
        pipeline_options.ocr_options = TesseractOcrOptions()

        converter = DocumentConverter(
            format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}
        )
        doc = converter.convert(str(image_pdf))

        elapsed = time.time() - start
        logger.info(f"  ✓ Docling + Tesseract completed in {elapsed:.1f}s")

        all_text_blocks = []

        if doc.document.texts:
            all_text_blocks.extend([item.text for item in doc.document.texts])

        if doc.document.tables:
            for table in doc.document.tables:
                table_md = table.export_to_markdown(doc.document)
                if table_md:
                    all_text_blocks.append(table_md)

        markdown_text = doc.document.export_to_markdown()

        output_path = (
            output_dir
            / f"{image_pdf.stem.replace('_grayscale_image_only', '')}_tesseract_extraction.json"
        )
        extraction_data = {
            "texts": all_text_blocks,
            "markdown_full_text": markdown_text,
            "page_count": len(doc.pages) if doc.pages else 0,
            "metadata": {
                "pipeline": "docling_tesseract",
                "ocr_engine": "tesseract",
                "extraction_time_s": elapsed,
                "text_blocks": len([item.text for item in doc.document.texts])
                if doc.document.texts
                else 0,
                "tables": len(list(doc.document.tables)) if doc.document.tables else 0,
            },
        }

        with open(output_path, "w") as f:
            json.dump(extraction_data, f, indent=2, default=str)

        logger.info(f"  ✓ Saved extraction: {output_path.name}")
        logger.info(
            f"      {len(extraction_data['texts'])} text blocks, {extraction_data['page_count']} pages"
        )

        return output_path

    except Exception as e:
        logger.error(f"  ✗ Docling + Tesseract failed: {e}")
        raise


def process_pdf(
    pdf_path: Path, image_dir: Path, extraction_dir: Path, baseline_dir: Path, comparison_dir: Path
) -> dict:
    """Process a single PDF through the full pipeline with comparison."""
    start_time = time.time()

    try:
        logger.info(f"\n{'=' * 80}")
        logger.info(f"Processing: {pdf_path.name}")
        logger.info(f"{'=' * 80}")

        # Step 1: Convert to grayscale image-only PDF
        image_pdf = create_grayscale_image_only_pdf(pdf_path, image_dir)

        # Step 2: Run Docling + Tesseract OCR
        extraction_path = run_docling_tesseract_ocr(image_pdf, extraction_dir)

        # Step 3: Compare with baseline if it exists
        baseline_path = baseline_dir / f"{pdf_path.stem}_baseline_extraction.json"
        comparison = None

        if baseline_path.exists():
            comparison = compare_extractions(extraction_path, baseline_path, comparison_dir)
        else:
            logger.info(f"\n⚠️  No baseline extraction found at: {baseline_path.name}")
            logger.info("    Skipping comparison for this PDF")

        elapsed = time.time() - start_time
        logger.info(f"\n✓ Completed {pdf_path.name} in {elapsed:.1f}s")

        return {
            "pdf": pdf_path.name,
            "success": True,
            "image_pdf": str(image_pdf),
            "extraction": str(extraction_path),
            "baseline_exists": baseline_path.exists(),
            "comparison": comparison,
            "time_s": elapsed,
            "error": None,
        }

    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"✗ Failed {pdf_path.name}: {e}")

        return {
            "pdf": pdf_path.name,
            "success": False,
            "image_pdf": None,
            "extraction": None,
            "baseline_exists": False,
            "comparison": None,
            "time_s": elapsed,
            "error": str(e),
        }


def main():
    """Run pipeline on entire corpus with comparisons."""
    # Set TESSDATA_PREFIX environment variable
    os.environ["TESSDATA_PREFIX"] = "/opt/homebrew/Cellar/tesseract/5.5.1/share/tessdata"

    # Define paths
    pdf_dir = Path("data/v3_data/raw_pdf")
    output_base = Path("results/tesseract_corpus_pipeline")
    image_dir = output_base / "grayscale_image_pdfs"
    extraction_dir = output_base / "tesseract_extractions"
    comparison_dir = output_base / "comparisons"
    baseline_dir = Path("results/ocr_pipeline_evaluation/extractions")

    # Create output directories
    image_dir.mkdir(parents=True, exist_ok=True)
    extraction_dir.mkdir(parents=True, exist_ok=True)
    comparison_dir.mkdir(parents=True, exist_ok=True)

    # Load ground truth metrics to sort PDFs by ocrmac performance
    metrics_file = Path("results/ocr_pipeline_evaluation/metrics/baseline_matching_metrics.csv")
    performance_map = {}

    if metrics_file.exists():
        with open(metrics_file) as f:
            reader = csv.DictReader(f)
            for row in reader:
                pdf_name = row["pdf_name"]
                body_recall = float(row["body_recall"])
                performance_map[pdf_name] = body_recall

        logger.info(f"Loaded performance metrics for {len(performance_map)} PDFs")

    # Get all PDFs and sort by performance (worst to best)
    all_pdfs = list(pdf_dir.glob("*.pdf"))

    # Separate PDFs with and without baseline metrics
    pdfs_with_metrics = []
    pdfs_without_metrics = []

    for pdf_path in all_pdfs:
        pdf_stem = pdf_path.stem
        if pdf_stem in performance_map:
            pdfs_with_metrics.append((pdf_path, performance_map[pdf_stem]))
        else:
            pdfs_without_metrics.append(pdf_path)

    # Sort PDFs with metrics by body_recall (worst to best)
    pdfs_with_metrics.sort(key=lambda x: x[1])

    # Combine: worst performers first, then PDFs without metrics
    pdf_files = [pdf for pdf, _ in pdfs_with_metrics] + sorted(pdfs_without_metrics)

    logger.info("=" * 80)
    logger.info("TESSERACT CORPUS PIPELINE WITH COMPARISON")
    logger.info("=" * 80)
    logger.info(f"Found {len(pdf_files)} PDFs in {pdf_dir}")
    logger.info(f"  - {len(pdfs_with_metrics)} with baseline metrics (sorted worst → best)")
    logger.info(f"  - {len(pdfs_without_metrics)} without baseline metrics")
    logger.info(f"Output directory: {output_base}")
    logger.info(f"Baseline directory: {baseline_dir}")
    logger.info(f"TESSDATA_PREFIX: {os.environ.get('TESSDATA_PREFIX')}")

    if pdfs_with_metrics:
        logger.info("\nProcessing order (by ocrmac body_recall):")
        for i, (pdf, recall) in enumerate(pdfs_with_metrics[:5], 1):
            logger.info(f"  {i}. {pdf.stem} (recall: {recall:.1%})")
        if len(pdfs_with_metrics) > 5:
            logger.info(f"  ... ({len(pdfs_with_metrics) - 5} more)")

    logger.info("=" * 80)

    # Process each PDF
    results = []
    start_time = time.time()

    for i, pdf_path in enumerate(pdf_files, 1):
        logger.info(f"\n[{i}/{len(pdf_files)}] Starting: {pdf_path.name}")

        result = process_pdf(pdf_path, image_dir, extraction_dir, baseline_dir, comparison_dir)
        results.append(result)

        # Save progress after each PDF
        progress_file = output_base / "pipeline_progress_with_comparison.json"
        with open(progress_file, "w") as f:
            json.dump({"completed": i, "total": len(pdf_files), "results": results}, f, indent=2)

    # Final summary
    total_time = time.time() - start_time
    success_count = sum(1 for r in results if r["success"])
    compared_count = sum(1 for r in results if r.get("baseline_exists"))

    logger.info("\n" + "=" * 80)
    logger.info("PIPELINE COMPLETE")
    logger.info("=" * 80)
    logger.info(f"Total time: {total_time / 60:.1f} minutes")
    logger.info(f"Successful: {success_count}/{len(pdf_files)}")
    logger.info(f"Compared with baseline: {compared_count}")
    logger.info(f"Failed: {len(pdf_files) - success_count}")

    # Calculate average improvements
    comparisons = [r["comparison"] for r in results if r.get("comparison")]
    if comparisons:
        avg_coverage = sum(c["coverage_pct"] for c in comparisons) / len(comparisons)
        avg_block_diff = sum(c["block_diff"] for c in comparisons) / len(comparisons)
        avg_char_diff = sum(c["char_diff"] for c in comparisons) / len(comparisons)

        logger.info("\n=== COMPARISON SUMMARY ===")
        logger.info(f"Average coverage: {avg_coverage:.1f}%")
        logger.info(f"Average block difference: {avg_block_diff:+.1f}")
        logger.info(f"Average character difference: {avg_char_diff:+,.0f}")

    # Save final results
    final_results = {
        "total_pdfs": len(pdf_files),
        "successful": success_count,
        "failed": len(pdf_files) - success_count,
        "compared_with_baseline": compared_count,
        "total_time_s": total_time,
        "avg_time_per_pdf_s": total_time / len(pdf_files) if pdf_files else 0,
        "results": results,
    }

    results_file = output_base / "pipeline_results_with_comparison.json"
    with open(results_file, "w") as f:
        json.dump(final_results, f, indent=2)

    logger.info(f"\n✓ Results saved to: {results_file}")


if __name__ == "__main__":
    main()
