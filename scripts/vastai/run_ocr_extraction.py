#!/usr/bin/env python3
"""
EasyOCR extraction script for vast.ai deployment.
Extracts text from PDFs and outputs multiple formats: text, JSON, CSV, annotated PDF.

Usage:
    python run_ocr_extraction.py --input input.pdf --output-dir ./results
    python run_ocr_extraction.py --batch --input-dir ./data --output-dir ./results
"""

import argparse
import csv
import json
from pathlib import Path

import easyocr
import fitz  # PyMuPDF


def setup_reader(gpu=True):
    """Initialize EasyOCR reader."""
    print("🔄 Initializing EasyOCR (models already pre-downloaded)...")
    reader = easyocr.Reader(["en"], gpu=gpu)
    print("✅ EasyOCR ready")
    return reader


def extract_text_from_pdf(pdf_path, reader):
    """
    Extract text from PDF using EasyOCR.
    Returns list of results with bounding boxes, text, and confidence.
    """
    print(f"📄 Processing: {pdf_path}")

    # Open PDF
    pdf = fitz.open(pdf_path)
    all_results = []

    for page_num in range(len(pdf)):
        print(f"  Page {page_num + 1}/{len(pdf)}...")

        # Get page
        page = pdf[page_num]

        # Convert page to image
        pix = page.get_pixmap(dpi=300)
        img_data = pix.tobytes("png")

        # Run OCR
        results = reader.readtext(img_data)

        # Add page number to results
        for bbox, text, conf in results:
            all_results.append(
                {
                    "page": page_num + 1,
                    "bbox": bbox,
                    "text": text,
                    "confidence": conf,
                }
            )

    pdf.close()
    print(f"✅ Extracted {len(all_results)} text blocks")
    return all_results


def save_text_output(results, output_path):
    """Save plain text output."""
    with open(output_path, "w", encoding="utf-8") as f:
        for result in results:
            f.write(result["text"] + "\n")
    print(f"💾 Saved text: {output_path}")


def save_json_output(results, output_path):
    """Save JSON output with bounding boxes and confidence."""
    # Convert numpy arrays to lists for JSON serialization
    json_results = []
    for r in results:
        json_results.append(
            {
                "page": r["page"],
                "bbox": [[float(x), float(y)] for x, y in r["bbox"]],
                "text": r["text"],
                "confidence": float(r["confidence"]),
            }
        )

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(json_results, f, indent=2, ensure_ascii=False)
    print(f"💾 Saved JSON: {output_path}")


def save_csv_output(results, output_path):
    """Save CSV output."""
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["page", "text", "confidence", "x1", "y1", "x2", "y2"])

        for r in results:
            bbox = r["bbox"]
            x_coords = [float(p[0]) for p in bbox]
            y_coords = [float(p[1]) for p in bbox]

            writer.writerow(
                [
                    r["page"],
                    r["text"],
                    f"{r['confidence']:.4f}",
                    min(x_coords),
                    min(y_coords),
                    max(x_coords),
                    max(y_coords),
                ]
            )
    print(f"💾 Saved CSV: {output_path}")


def create_annotated_pdf(pdf_path, results, output_path):
    """Create annotated PDF with bounding boxes and extracted text."""
    print("📝 Creating annotated PDF...")

    pdf = fitz.open(pdf_path)

    for result in results:
        page_num = result["page"] - 1  # 0-indexed
        page = pdf[page_num]

        # Draw bounding box
        bbox = result["bbox"]
        x_coords = [float(p[0]) for p in bbox]
        y_coords = [float(p[1]) for p in bbox]

        rect = fitz.Rect(min(x_coords), min(y_coords), max(x_coords), max(y_coords))

        # Add rectangle annotation (green for high confidence, yellow for low)
        color = (0, 1, 0) if result["confidence"] > 0.8 else (1, 1, 0)
        page.draw_rect(rect, color=color, width=1)

        # Add text annotation
        text_annotation = f"{result['text']}\n(conf: {result['confidence']:.2f})"
        page.add_freetext_annot(rect, text_annotation, fontsize=8, fill_color=(1, 1, 0.8))

    pdf.save(output_path)
    pdf.close()
    print(f"💾 Saved annotated PDF: {output_path}")


def process_single_pdf(pdf_path, output_dir, reader):
    """Process a single PDF and generate all outputs."""
    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    stem = pdf_path.stem

    # Extract text
    results = extract_text_from_pdf(pdf_path, reader)

    # Save all formats
    save_text_output(results, output_dir / f"{stem}.txt")
    save_json_output(results, output_dir / f"{stem}.json")
    save_csv_output(results, output_dir / f"{stem}.csv")
    create_annotated_pdf(pdf_path, results, output_dir / f"{stem}_annotated.pdf")

    print(f"\n✅ Completed: {pdf_path.name}")
    print(f"   Text blocks: {len(results)}")
    print(f"   Avg confidence: {sum(r['confidence'] for r in results) / len(results):.2%}")
    print(f"   Outputs: {output_dir / stem}.*\n")


def process_batch(input_dir, output_dir, reader):
    """Process all PDFs in a directory."""
    input_dir = Path(input_dir)
    pdf_files = list(input_dir.glob("*.pdf"))

    print(f"📁 Found {len(pdf_files)} PDFs in {input_dir}\n")

    for i, pdf_path in enumerate(pdf_files, 1):
        print(f"=== Processing {i}/{len(pdf_files)} ===")
        try:
            process_single_pdf(pdf_path, output_dir, reader)
        except Exception as e:
            print(f"❌ Error processing {pdf_path.name}: {e}\n")
            continue

    print(f"\n✅ Batch complete! Processed {len(pdf_files)} PDFs")


def main():
    parser = argparse.ArgumentParser(
        description="EasyOCR extraction with multiple output formats",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single PDF
  python run_ocr_extraction.py --input paper.pdf --output-dir ./results

  # Batch processing
  python run_ocr_extraction.py --batch --input-dir ./data --output-dir ./results

  # Use CPU instead of GPU
  python run_ocr_extraction.py --input paper.pdf --output-dir ./results --no-gpu
        """,
    )

    parser.add_argument("--input", type=str, help="Input PDF file")
    parser.add_argument("--input-dir", type=str, help="Input directory for batch processing")
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./results",
        help="Output directory (default: ./results)",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Batch process all PDFs in input-dir",
    )
    parser.add_argument(
        "--no-gpu",
        action="store_true",
        help="Use CPU instead of GPU",
    )

    args = parser.parse_args()

    # Validate arguments
    if args.batch:
        if not args.input_dir:
            parser.error("--input-dir required when using --batch")
        if not Path(args.input_dir).exists():
            parser.error(f"Input directory not found: {args.input_dir}")
    else:
        if not args.input:
            parser.error("--input required for single file processing")
        if not Path(args.input).exists():
            parser.error(f"Input file not found: {args.input}")

    # Initialize reader
    reader = setup_reader(gpu=not args.no_gpu)

    # Process
    if args.batch:
        process_batch(args.input_dir, args.output_dir, reader)
    else:
        process_single_pdf(args.input, args.output_dir, reader)


if __name__ == "__main__":
    main()
