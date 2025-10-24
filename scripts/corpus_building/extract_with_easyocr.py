#!/usr/bin/env python3
"""
Extract text blocks from PDF using EasyOCR.

Usage:
    uv run python scripts/corpus_building/extract_with_easyocr.py --pdf political_mootness
    uv run python scripts/corpus_building/extract_with_easyocr.py --pdf political_mootness --dpi 300
"""

import argparse
import os
import re
import time
import unicodedata
from pathlib import Path

import easyocr
import fitz
import pandas as pd
from pdf2image import convert_from_path


def normalize_text_for_rag(text: str) -> str:
    """Normalize text for RAG: keep only letters, numbers, basic punctuation."""
    # Normalize smart quotes and dashes
    text = text.replace(""", "'").replace(""", "'")
    text = text.replace('"', '"').replace('"', '"')
    text = text.replace("—", "-").replace("–", "-")

    # Remove control characters (keep normal whitespace)
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]", "", text)

    # Keep only allowed characters
    allowed_chars = []
    for char in text:
        if char.isascii() and (char.isalnum() or char in " .,!?:;'\"-()[]/&\n\t") or char in "§¶[]":
            allowed_chars.append(char)
        elif unicodedata.category(char).startswith("L"):
            try:
                decomposed = unicodedata.normalize("NFD", char)
                if decomposed[0].isascii():
                    allowed_chars.append(char)
            except:
                pass

    text = "".join(allowed_chars)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def create_image_only_pdf(pdf_path: Path, output_dir: Path, dpi: int = 600) -> Path:
    """Create greyscale image-only PDF at specified DPI."""
    output_path = output_dir / f"{pdf_path.stem}_image_only_{dpi}dpi_easyocr.pdf"

    if output_path.exists():
        print(f"  Using cached image-only PDF: {output_path.name}")
        return output_path

    print(f"  Creating greyscale image-only PDF at {dpi} DPI...")

    src_doc = fitz.open(str(pdf_path))
    total_pages = len(src_doc)

    img_doc = fitz.open()

    for i in range(total_pages):
        if (i + 1) % 10 == 0:
            print(f"    Page {i + 1}/{total_pages}...")

        page = src_doc[i]

        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat, colorspace=fitz.csGRAY)

        img_page = img_doc.new_page(width=page.rect.width, height=page.rect.height)
        img_page.insert_image(img_page.rect, pixmap=pix)

    img_doc.save(str(output_path))
    img_doc.close()
    src_doc.close()

    print(f"  ✓ Created: {output_path.name} ({total_pages} pages)")
    return output_path


def extract_text_blocks_with_easyocr(image_pdf: Path, dpi: int = 600) -> list[dict]:
    """Extract text blocks with bounding boxes using EasyOCR."""
    print("  Initializing EasyOCR...")

    # Initialize reader with GPU support
    reader = easyocr.Reader(["en"], gpu=True, verbose=False)

    print(f"  Running OCR with EasyOCR ({dpi} DPI)...")

    # Get page dimensions
    src_doc = fitz.open(str(image_pdf))
    page_dimensions = [(page.rect.width, page.rect.height) for page in src_doc]
    src_doc.close()

    # Convert PDF to images
    images = convert_from_path(str(image_pdf), dpi=dpi, grayscale=True)

    if len(images) != len(page_dimensions):
        raise ValueError(
            f"Page count mismatch: {len(images)} images vs {len(page_dimensions)} pages"
        )

    all_blocks = []
    total_pages = len(images)

    for page_idx, img in enumerate(images):
        page_num = page_idx + 1

        if page_num % 10 == 0:
            print(f"    Page {page_num}/{total_pages}...")

        # Save temporary image
        temp_img = f"/tmp/easyocr_page_{page_idx}.png"
        img.save(temp_img)

        # Run EasyOCR with paragraph=True to combine text into larger blocks
        # workers=0 is faster on Mac M1 (GPU already parallelized via MPS)
        # For NVIDIA GPUs, try workers=4, 8, or 12 for better CPU/GPU balance
        num_workers = int(os.getenv("EASYOCR_WORKERS", "0"))
        result = reader.readtext(temp_img, paragraph=True, workers=num_workers)

        # Get page dimensions
        page_width, page_height = page_dimensions[page_idx]

        # Extract blocks with bounding boxes
        # Note: paragraph=True returns (bbox, text) tuples without confidence
        for item in result:
            if len(item) == 3:
                bbox, text, confidence = item
            elif len(item) == 2:
                bbox, text = item
                confidence = 1.0  # No confidence score in paragraph mode
            else:
                continue
            # bbox format from EasyOCR: [[x0,y0], [x1,y0], [x1,y1], [x0,y1]]
            # Convert to min/max coordinates
            x_coords = [point[0] for point in bbox]
            y_coords = [point[1] for point in bbox]

            x0_abs = min(x_coords)
            y0_abs = min(y_coords)
            x1_abs = max(x_coords)
            y1_abs = max(y_coords)

            # Normalize to 0-1 range
            # EasyOCR works on pixel coordinates, need to convert to PDF coordinates
            # Image size at dpi vs PDF page size
            x0_norm = x0_abs / (page_width * dpi / 72)
            y0_norm = y0_abs / (page_height * dpi / 72)
            x1_norm = x1_abs / (page_width * dpi / 72)
            y1_norm = y1_abs / (page_height * dpi / 72)

            # Normalize text
            normalized_text = normalize_text_for_rag(text)

            if normalized_text:
                all_blocks.append(
                    {
                        "page_number": page_num,
                        "text": normalized_text,
                        "x0": x0_norm,
                        "y0": y0_norm,
                        "x1": x1_norm,
                        "y1": y1_norm,
                        "confidence": confidence,
                    }
                )

    print(f"  ✓ Extracted {len(all_blocks)} text blocks from {total_pages} pages")
    return all_blocks


def calculate_features(blocks: list[dict]) -> pd.DataFrame:
    """Calculate features for classification."""
    df = pd.DataFrame(blocks)

    df["y_position_normalized"] = df["y0"]

    df["font_size"] = df["y1"] - df["y0"]

    page_medians = df.groupby("page_number")["font_size"].median().to_dict()
    df["normalized_font_size"] = df.apply(
        lambda row: row["font_size"] / page_medians[row["page_number"]]
        if page_medians[row["page_number"]] > 0
        else 1.0,
        axis=1,
    )

    feature_df = df[
        [
            "page_number",
            "y_position_normalized",
            "normalized_font_size",
            "text",
            "confidence",
            "x0",
            "y0",
            "x1",
            "y1",
        ]
    ]

    return feature_df


def main():
    parser = argparse.ArgumentParser(description="Extract text blocks from PDF using EasyOCR")
    parser.add_argument("--pdf", required=True, help="PDF name (without .pdf extension)")
    parser.add_argument(
        "--dpi", type=int, default=600, help="DPI for image rendering (default: 600)"
    )
    args = parser.parse_args()

    pdf_path = Path(f"data/v3_data/raw_pdf/{args.pdf}.pdf")
    if not pdf_path.exists():
        print(f"Error: PDF not found: {pdf_path}")
        return

    output_dir = Path("results/text_block_extraction")
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'=' * 60}")
    print("OCR Text Block Extraction (EasyOCR)")
    print(f"{'=' * 60}")
    print(f"PDF: {args.pdf}")
    print(f"DPI: {args.dpi}")
    print("Engine: EasyOCR")
    print()

    start_time = time.time()

    print("[Stage 1] Creating image-only PDF...")
    image_pdf = create_image_only_pdf(pdf_path, output_dir, args.dpi)

    print("\n[Stage 2] Extracting text blocks with EasyOCR...")
    blocks = extract_text_blocks_with_easyocr(image_pdf, args.dpi)

    print("\n[Stage 3] Calculating features...")
    df = calculate_features(blocks)

    output_file = output_dir / f"{args.pdf}_{args.dpi}dpi_blocks_v1_easyocr.csv"
    df.to_csv(output_file, index=False)

    elapsed = time.time() - start_time

    print(f"\n{'=' * 60}")
    print("Summary")
    print(f"{'=' * 60}")
    print(f"Blocks extracted: {len(df):,}")
    print(f"Total time: {elapsed:.1f}s")
    print(f"Speed: {len(df) / elapsed:.1f} blocks/sec")
    print()
    print(f"Output saved to: {output_file}")
    print()
    print("Next step: Auto-labeling (Stage 3)")
    print(
        f"  Run: uv run python scripts/corpus_building/auto_label_ocr_blocks.py --pdf {args.pdf} --dpi {args.dpi} --suffix _easyocr"
    )


if __name__ == "__main__":
    main()
