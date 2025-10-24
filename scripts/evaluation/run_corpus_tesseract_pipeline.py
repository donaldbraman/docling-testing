#!/usr/bin/env python3
"""
Run full corpus through: Grayscale Image-only PDF → Docling + Tesseract OCR pipeline.

This script processes all PDFs in data/v3_data/raw_pdf/ with:
1. Convert to grayscale image-only PDF (300 DPI)
2. Run Docling with Tesseract OCR
3. Extract text with semantic structure
4. Save results for comparison with ground truth

Usage:
    uv run python scripts/evaluation/run_corpus_tesseract_pipeline.py

    # Or in background:
    nohup uv run python scripts/evaluation/run_corpus_tesseract_pipeline.py > corpus_tesseract_pipeline.log 2>&1 &
"""

import json
import logging
import os
import time
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def create_grayscale_image_only_pdf(pdf_path: Path, output_dir: Path) -> Path:
    """Create grayscale image-only PDF by rasterizing all pages.

    Args:
        pdf_path: Path to original PDF
        output_dir: Output directory for image-only PDF

    Returns:
        Path to grayscale image-only PDF
    """
    import fitz  # PyMuPDF

    output_path = output_dir / f"{pdf_path.stem}_grayscale_image_only.pdf"

    if output_path.exists():
        logger.info(f"  Using cached grayscale PDF: {output_path.name}")
        return output_path

    logger.info(f"  Creating grayscale image-only PDF from: {pdf_path.name}")

    # Open original PDF
    src_doc = fitz.open(str(pdf_path))
    total_pages = len(src_doc)

    # Create new PDF document
    img_doc = fitz.open()

    # Render each page as grayscale image and add to new PDF
    for i in range(total_pages):
        # Get page
        page = src_doc[i]

        # Render page to grayscale image at 300 DPI
        mat = fitz.Matrix(300 / 72, 300 / 72)  # 300 DPI scaling
        pix = page.get_pixmap(matrix=mat, colorspace="gray")  # Grayscale

        # Create new page with same dimensions
        img_page = img_doc.new_page(width=page.rect.width, height=page.rect.height)

        # Insert grayscale image
        img_page.insert_image(img_page.rect, pixmap=pix)

    # Save grayscale image-only PDF
    img_doc.save(str(output_path))
    img_doc.close()
    src_doc.close()

    logger.info(f"  ✓ Created grayscale image-only PDF: {total_pages} pages")
    return output_path


def run_docling_tesseract_ocr(image_pdf: Path, output_dir: Path) -> Path:
    """Run Docling with Tesseract OCR and extract text.

    Args:
        image_pdf: Path to image-only PDF
        output_dir: Output directory for extraction JSON

    Returns:
        Path to extraction JSON
    """
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions, TesseractOcrOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption

    logger.info("  Running Docling with Tesseract OCR...")
    start = time.time()

    try:
        # Configure pipeline to use Tesseract
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = True
        pipeline_options.ocr_options = TesseractOcrOptions()

        # Run Docling with Tesseract OCR
        converter = DocumentConverter(
            format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}
        )
        doc = converter.convert(str(image_pdf))

        elapsed = time.time() - start
        logger.info(f"  ✓ Docling + Tesseract completed in {elapsed:.1f}s")

        # Collect all text blocks
        all_text_blocks = []

        # Add text items
        if doc.document.texts:
            all_text_blocks.extend([item.text for item in doc.document.texts])

        # Add table content (export as markdown to preserve structure)
        if doc.document.tables:
            for table in doc.document.tables:
                table_md = table.export_to_markdown(doc.document)
                if table_md:
                    all_text_blocks.append(table_md)

        # Export full markdown
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


def process_pdf(pdf_path: Path, image_dir: Path, extraction_dir: Path) -> dict:
    """Process a single PDF through the full pipeline.

    Args:
        pdf_path: Path to original PDF
        image_dir: Directory for image-only PDFs
        extraction_dir: Directory for extraction JSONs

    Returns:
        Processing results dict
    """
    start_time = time.time()

    try:
        # Step 1: Convert to grayscale image-only PDF
        logger.info(f"\n{'=' * 80}")
        logger.info(f"Processing: {pdf_path.name}")
        logger.info(f"{'=' * 80}")

        image_pdf = create_grayscale_image_only_pdf(pdf_path, image_dir)

        # Step 2: Run Docling + Tesseract OCR
        extraction_path = run_docling_tesseract_ocr(image_pdf, extraction_dir)

        elapsed = time.time() - start_time
        logger.info(f"✓ Completed {pdf_path.name} in {elapsed:.1f}s")

        return {
            "pdf": pdf_path.name,
            "success": True,
            "image_pdf": str(image_pdf),
            "extraction": str(extraction_path),
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
            "time_s": elapsed,
            "error": str(e),
        }


def main():
    """Run pipeline on entire corpus."""
    # Set TESSDATA_PREFIX environment variable
    os.environ["TESSDATA_PREFIX"] = "/opt/homebrew/Cellar/tesseract/5.5.1/share/tessdata"

    # Define paths
    pdf_dir = Path("data/v3_data/raw_pdf")
    output_base = Path("results/tesseract_corpus_pipeline")
    image_dir = output_base / "grayscale_image_pdfs"
    extraction_dir = output_base / "tesseract_extractions"

    # Create output directories
    image_dir.mkdir(parents=True, exist_ok=True)
    extraction_dir.mkdir(parents=True, exist_ok=True)

    # Get all PDFs
    pdf_files = sorted(pdf_dir.glob("*.pdf"))

    logger.info("=" * 80)
    logger.info("TESSERACT CORPUS PIPELINE")
    logger.info("=" * 80)
    logger.info(f"Found {len(pdf_files)} PDFs in {pdf_dir}")
    logger.info(f"Output directory: {output_base}")
    logger.info(f"TESSDATA_PREFIX: {os.environ.get('TESSDATA_PREFIX')}")
    logger.info("=" * 80)

    # Process each PDF
    results = []
    start_time = time.time()

    for i, pdf_path in enumerate(pdf_files, 1):
        logger.info(f"\n[{i}/{len(pdf_files)}] Starting: {pdf_path.name}")

        result = process_pdf(pdf_path, image_dir, extraction_dir)
        results.append(result)

        # Save progress after each PDF
        progress_file = output_base / "pipeline_progress.json"
        with open(progress_file, "w") as f:
            json.dump({"completed": i, "total": len(pdf_files), "results": results}, f, indent=2)

    # Final summary
    total_time = time.time() - start_time
    success_count = sum(1 for r in results if r["success"])

    logger.info("\n" + "=" * 80)
    logger.info("PIPELINE COMPLETE")
    logger.info("=" * 80)
    logger.info(f"Total time: {total_time / 60:.1f} minutes")
    logger.info(f"Successful: {success_count}/{len(pdf_files)}")
    logger.info(f"Failed: {len(pdf_files) - success_count}")

    # Save final results
    final_results = {
        "total_pdfs": len(pdf_files),
        "successful": success_count,
        "failed": len(pdf_files) - success_count,
        "total_time_s": total_time,
        "avg_time_per_pdf_s": total_time / len(pdf_files) if pdf_files else 0,
        "results": results,
    }

    results_file = output_base / "pipeline_results.json"
    with open(results_file, "w") as f:
        json.dump(final_results, f, indent=2)

    logger.info(f"\n✓ Results saved to: {results_file}")


if __name__ == "__main__":
    main()
