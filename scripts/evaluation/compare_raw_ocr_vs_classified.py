#!/usr/bin/env python3
"""
Compare raw OCR output vs Docling classified output.

Shows what text layout detection is discarding.
"""

from pathlib import Path

import fitz  # PyMuPDF
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import OcrMacOptions, PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption


def extract_raw_ocr_text(pdf_path: Path, engine: str = "ocrmac") -> str:
    """
    Extract ALL text that OCR detects, without layout filtering.

    Uses PyMuPDF's direct OCR to get unfiltered text.
    """
    import platform

    doc = fitz.open(pdf_path)
    all_text = []

    for page_num in range(len(doc)):
        page = doc[page_num]

        if engine == "ocrmac" and platform.system() == "Darwin":
            # Use macOS OCR directly
            pix = page.get_pixmap(dpi=300)
            ocr_result = pix.pdfocr_tobytes(language="eng", tessdata=None)
            # Extract text from OCR PDF
            ocr_doc = fitz.open("pdf", ocr_result)
            page_text = ocr_doc[0].get_text()
            ocr_doc.close()
        else:
            # Fallback: use Tesseract via PyMuPDF
            import pytesseract
            from PIL import Image

            pix = page.get_pixmap(dpi=300)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            page_text = pytesseract.image_to_string(img)

        all_text.append(page_text)

    doc.close()
    return "\n\n".join(all_text)


def extract_docling_text(pdf_path: Path, engine: str = "ocrmac") -> str:
    """Extract text through Docling's full pipeline (with layout classification)."""
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = True
    pipeline_options.ocr_options = OcrMacOptions() if engine == "ocrmac" else None

    converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}
    )

    doc = converter.convert(str(pdf_path))
    return "\n\n".join(item.text for item in doc.document.texts if hasattr(item, "text"))


def get_stats(text: str) -> dict:
    """Get text statistics."""
    return {
        "chars": len(text),
        "chars_no_ws": len(text.replace(" ", "").replace("\n", "").replace("\t", "")),
        "words": len(text.split()),
        "lines": len(text.split("\n")),
    }


def find_missing_lines(raw_text: str, classified_text: str) -> list[str]:
    """Find lines present in raw OCR but missing from classified output."""
    raw_lines = {line.strip() for line in raw_text.split("\n") if line.strip()}
    classified_lines = {line.strip() for line in classified_text.split("\n") if line.strip()}

    missing = raw_lines - classified_lines
    return sorted(missing)


def main():
    """Compare raw OCR vs Docling classified output."""
    pdf_path = Path(
        "results/ocr_engine_comparison/academic_limbo__reforming_campus_speech_governance_for_students_image_only.pdf"
    )
    output_dir = Path("results/ocr_vs_classified")
    output_dir.mkdir(parents=True, exist_ok=True)

    if not pdf_path.exists():
        print(f"Error: {pdf_path} not found")
        return 1

    print("=" * 80)
    print("Extracting Raw OCR (unfiltered)")
    print("=" * 80)
    raw_text = extract_raw_ocr_text(pdf_path)
    raw_stats = get_stats(raw_text)

    raw_path = output_dir / "raw_ocr.txt"
    raw_path.write_text(raw_text, encoding="utf-8")

    print(f"  Characters: {raw_stats['chars']:,}")
    print(f"  Characters (no whitespace): {raw_stats['chars_no_ws']:,}")
    print(f"  Words: {raw_stats['words']:,}")
    print(f"  Lines: {raw_stats['lines']:,}")
    print(f"  Saved: {raw_path}")

    print("\n" + "=" * 80)
    print("Extracting Docling Classified (filtered by layout detection)")
    print("=" * 80)
    classified_text = extract_docling_text(pdf_path)
    classified_stats = get_stats(classified_text)

    classified_path = output_dir / "docling_classified.txt"
    classified_path.write_text(classified_text, encoding="utf-8")

    print(f"  Characters: {classified_stats['chars']:,}")
    print(f"  Characters (no whitespace): {classified_stats['chars_no_ws']:,}")
    print(f"  Words: {classified_stats['words']:,}")
    print(f"  Lines: {classified_stats['lines']:,}")
    print(f"  Saved: {classified_path}")

    print("\n" + "=" * 80)
    print("COMPARISON")
    print("=" * 80)

    char_lost = raw_stats["chars"] - classified_stats["chars"]
    char_nows_lost = raw_stats["chars_no_ws"] - classified_stats["chars_no_ws"]
    word_lost = raw_stats["words"] - classified_stats["words"]
    line_lost = raw_stats["lines"] - classified_stats["lines"]

    print("\nText LOST by layout detection:")
    print(f"  Characters: {char_lost:,} ({char_lost / raw_stats['chars'] * 100:.2f}%)")
    print(
        f"  Characters (no whitespace): {char_nows_lost:,} ({char_nows_lost / raw_stats['chars_no_ws'] * 100:.2f}%)"
    )
    print(f"  Words: {word_lost:,} ({word_lost / raw_stats['words'] * 100:.2f}%)")
    print(f"  Lines: {line_lost:,}")

    # Find missing lines
    print("\n" + "=" * 80)
    print("Finding Missing Lines...")
    print("=" * 80)

    missing_lines = find_missing_lines(raw_text, classified_text)

    print(f"\nFound {len(missing_lines)} lines in raw OCR but NOT in classified output")

    if missing_lines:
        missing_path = output_dir / "missing_lines.txt"
        missing_path.write_text("\n".join(missing_lines), encoding="utf-8")
        print(f"Saved: {missing_path}")

        print("\nFirst 20 missing lines:")
        for i, line in enumerate(missing_lines[:20], 1):
            print(f"  {i}. {line[:80]}{'...' if len(line) > 80 else ''}")

        if len(missing_lines) > 20:
            print(f"  ... and {len(missing_lines) - 20} more")

    print(f"\n✓ All files saved to: {output_dir}")
    return 0


if __name__ == "__main__":
    exit(main())
