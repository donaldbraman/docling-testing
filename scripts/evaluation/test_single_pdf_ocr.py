#!/usr/bin/env python3
"""
Test OCR pipeline on a single PDF with full page processing.

Usage:
  python3 scripts/evaluation/test_single_pdf_ocr.py --pdf political_mootness --method ocrmypdf
"""

import argparse
import json
import logging
import subprocess
import time
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def create_image_only_pdf(pdf_path: Path, output_dir: Path, max_pages: int | None = None) -> Path:
    """Create image-only PDF by rasterizing ALL pages using PyMuPDF.

    Args:
        pdf_path: Path to original PDF
        output_dir: Output directory
        max_pages: Maximum pages to process (None = all pages)

    Returns:
        Path to image-only PDF
    """
    import fitz  # PyMuPDF

    output_path = output_dir / f"{pdf_path.stem}_image_only.pdf"

    if output_path.exists():
        logger.info(f"  Using cached image-only PDF: {output_path.name}")
        return output_path

    logger.info(f"  Creating image-only PDF from: {pdf_path.name}")
    logger.info(f"  Processing: {'ALL pages' if max_pages is None else f'first {max_pages} pages'}")

    # Open original PDF
    src_doc = fitz.open(str(pdf_path))

    # Determine page range
    total_pages = len(src_doc)
    page_count = min(max_pages, total_pages) if max_pages else total_pages

    # Create new PDF document
    img_doc = fitz.open()

    # Render each page as image and add to new PDF
    for i in range(page_count):
        logger.info(f"    Converting page {i + 1}/{page_count} to image...")

        # Get page
        page = src_doc[i]

        # Render page to image at 300 DPI
        mat = fitz.Matrix(300 / 72, 300 / 72)  # 300 DPI scaling
        pix = page.get_pixmap(matrix=mat)

        # Create new page with same dimensions
        img_page = img_doc.new_page(width=page.rect.width, height=page.rect.height)

        # Insert image
        img_page.insert_image(img_page.rect, pixmap=pix)

    # Save image-only PDF
    img_doc.save(str(output_path))
    img_doc.close()
    src_doc.close()

    logger.info(f"  ✓ Created image-only PDF: {page_count} pages")
    return output_path


def run_docling_ocr(image_pdf: Path, output_dir: Path) -> Path:
    """Run Docling's internal OCR and extract text directly.

    Args:
        image_pdf: Path to image-only PDF
        output_dir: Output directory

    Returns:
        Path to extraction JSON
    """
    from docling.document_converter import DocumentConverter

    logger.info("  Running Docling internal OCR...")
    start = time.time()

    try:
        # Run Docling with internal OCR on image-only PDF
        converter = DocumentConverter()
        doc = converter.convert(str(image_pdf))

        elapsed = time.time() - start
        logger.info(f"  ✓ Docling OCR completed in {elapsed:.1f}s")

        # Save extraction
        output_path = output_dir / f"{image_pdf.stem}_baseline_extraction.json"
        extraction_data = {
            "texts": list(doc.document.texts) if doc.document.texts else [],
            "page_count": len(doc.pages) if doc.pages else 0,
            "metadata": {
                "pipeline": "baseline",
                "extraction_time_s": elapsed,
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
        logger.error(f"  ✗ Docling OCR failed: {e}")
        raise RuntimeError(f"Docling OCR failed: {e}") from e


def run_ocrmypdf(image_pdf: Path, output_dir: Path) -> Path:
    """Run OCRmyPDF to add text layer.

    Args:
        image_pdf: Path to image-only PDF
        output_dir: Output directory

    Returns:
        Path to OCR'd PDF
    """
    output_path = output_dir / f"{image_pdf.stem}_ocr.pdf"

    if output_path.exists():
        logger.info(f"  Using cached OCR PDF: {output_path.name}")
        return output_path

    logger.info("  Running OCRmyPDF (Tesseract)...")
    start = time.time()

    # Run OCRmyPDF with progress tracking
    cmd = [
        "ocrmypdf",
        "--language",
        "eng",
        "--force-ocr",  # Force OCR even if text layer exists
        "--output-type",
        "pdf",
        str(image_pdf),
        str(output_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        logger.error(f"  ✗ OCRmyPDF failed: {result.stderr}")
        raise RuntimeError(f"OCRmyPDF failed: {result.stderr}")

    elapsed = time.time() - start
    logger.info(f"  ✓ OCRmyPDF completed in {elapsed:.1f}s")

    return output_path


def run_paddleocr(image_pdf: Path, output_dir: Path) -> Path:
    """Run PaddleOCR to extract text.

    Args:
        image_pdf: Path to image-only PDF
        output_dir: Output directory

    Returns:
        Path to extraction JSON
    """
    logger.info("  Running PaddleOCR...")
    start = time.time()

    try:
        import pdf2image
        from paddleocr import PaddleOCR

        # Initialize PaddleOCR with GPU if available
        ocr = PaddleOCR(use_gpu=True, lang="en")

        # Convert PDF to images
        images = pdf2image.convert_from_path(str(image_pdf), dpi=300)
        logger.info(f"    Processing {len(images)} pages...")

        # Run OCR on each page
        all_texts = []
        for i, image in enumerate(images, 1):
            logger.info(f"    Page {i}/{len(images)}...")
            result = ocr.ocr(image, cls=True)

            # Extract text from OCR result
            if result and result[0]:
                page_texts = [line[1][0] for line in result[0]]
                all_texts.extend(page_texts)

        elapsed = time.time() - start
        logger.info(f"  ✓ PaddleOCR completed in {elapsed:.1f}s")

        # Save extraction in same format as other methods
        output_path = output_dir / f"{image_pdf.stem}_paddleocr_extraction.json"
        extraction_data = {
            "texts": all_texts,
            "page_count": len(images),
            "metadata": {
                "pipeline": "paddleocr",
                "extraction_time_s": elapsed,
            },
        }

        with open(output_path, "w") as f:
            json.dump(extraction_data, f, indent=2, default=str)

        logger.info(f"  ✓ Saved extraction: {output_path.name}")
        logger.info(f"      {len(all_texts)} text blocks, {len(images)} pages")

        return output_path

    except ImportError as e:
        logger.error(f"  ✗ PaddleOCR not installed: {e}")
        raise RuntimeError(f"PaddleOCR not installed: {e}") from e


def extract_with_docling(pdf_path: Path, output_dir: Path, pipeline_name: str) -> Path:
    """Extract text using Docling.

    Args:
        pdf_path: Path to PDF
        output_dir: Output directory
        pipeline_name: Pipeline name for output file

    Returns:
        Path to extraction JSON
    """
    from docling.document_converter import DocumentConverter

    logger.info("  Running Docling text extraction...")
    start = time.time()

    converter = DocumentConverter()
    doc = converter.convert(str(pdf_path))

    elapsed = time.time() - start
    logger.info(f"  ✓ Docling completed in {elapsed:.1f}s")

    # Save extraction
    output_path = output_dir / f"{pdf_path.stem}_{pipeline_name}_extraction.json"
    extraction_data = {
        "texts": list(doc.document.texts) if doc.document.texts else [],
        "page_count": len(doc.pages) if doc.pages else 0,
        "metadata": {
            "pipeline": pipeline_name,
            "extraction_time_s": elapsed,
        },
    }

    with open(output_path, "w") as f:
        json.dump(extraction_data, f, indent=2, default=str)

    logger.info(f"  ✓ Saved extraction: {output_path.name}")
    logger.info(
        f"      {len(extraction_data['texts'])} text blocks, {extraction_data['page_count']} pages"
    )

    return output_path


def count_pdf_pages(pdf_path: Path) -> int:
    """Count pages in PDF."""
    import PyPDF2

    with open(pdf_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        return len(reader.pages)


def main():
    """Test OCR pipeline on single PDF."""
    parser = argparse.ArgumentParser(description="Test OCR pipeline on single PDF")
    parser.add_argument(
        "--pdf",
        type=str,
        required=True,
        help="PDF name (without .pdf extension)",
    )
    parser.add_argument(
        "--method",
        type=str,
        choices=["baseline", "ocrmypdf", "paddleocr"],
        default="ocrmypdf",
        help="Extraction method to test",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Maximum pages to process (default: all pages)",
    )
    parser.add_argument(
        "--skip-completeness",
        action="store_true",
        help="Skip completeness test",
    )

    args = parser.parse_args()

    # Setup paths
    pdf_path = Path(f"data/v3_data/raw_pdf/{args.pdf}.pdf")
    ground_truth_path = Path(
        f"results/ocr_pipeline_evaluation/ground_truth/{args.pdf}_ground_truth.json"
    )

    output_dir = Path("results/ocr_pipeline_test")
    output_dir.mkdir(parents=True, exist_ok=True)

    if not pdf_path.exists():
        logger.error(f"PDF not found: {pdf_path}")
        return 1

    if not ground_truth_path.exists():
        logger.error(f"Ground truth not found: {ground_truth_path}")
        logger.info("Run html_ground_truth_extractor.py first to create ground truth")
        return 1

    # Count pages
    total_pages = count_pdf_pages(pdf_path)

    logger.info("=" * 80)
    logger.info("OCR PIPELINE TEST (SINGLE PDF)")
    logger.info("=" * 80)
    logger.info(f"\nPDF: {args.pdf}.pdf")
    logger.info(f"Total pages: {total_pages}")
    logger.info(f"Method: {args.method}")
    logger.info(f"Max pages: {args.max_pages if args.max_pages else 'ALL'}\n")

    try:
        # Step 1: Create image-only PDF
        logger.info("[1/3] Creating image-only PDF...")
        image_pdf = create_image_only_pdf(pdf_path, output_dir, args.max_pages)

        # Step 2 & 3: Run OCR and extract text
        if args.method == "baseline":
            logger.info("\n[2/3] Running Docling internal OCR...")
            extraction_path = run_docling_ocr(image_pdf, output_dir)
            logger.info("\n[3/3] Baseline extraction complete...")
        elif args.method == "ocrmypdf":
            logger.info("\n[2/3] Running OCRmyPDF (Tesseract)...")
            ocr_pdf = run_ocrmypdf(image_pdf, output_dir)
            logger.info("\n[3/3] Extracting text from OCR'd PDF...")
            extraction_path = extract_with_docling(ocr_pdf, output_dir, args.method)
        elif args.method == "paddleocr":
            logger.info("\n[2/3] Running PaddleOCR...")
            extraction_path = run_paddleocr(image_pdf, output_dir)
            logger.info("\n[3/3] PaddleOCR extraction complete...")

        logger.info("\n" + "=" * 80)
        logger.info("EXTRACTION COMPLETE")
        logger.info("=" * 80)
        logger.info(f"\nExtraction saved to: {extraction_path}")

        # Run completeness test if requested
        if not args.skip_completeness:
            logger.info("\n" + "=" * 80)
            logger.info("RUNNING COMPLETENESS TEST")
            logger.info("=" * 80)

            # Import and run completeness test
            import subprocess

            result = subprocess.run(
                [
                    "python3",
                    "scripts/evaluation/test_ocr_completeness.py",
                    "--extraction",
                    str(extraction_path),
                    "--ground-truth",
                    str(ground_truth_path),
                    "--pdf-pages",
                    str(total_pages),
                    "--verbose",
                ],
                check=False,
            )

            return result.returncode

        return 0

    except Exception as e:
        logger.error(f"\n✗ Error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit(main())
