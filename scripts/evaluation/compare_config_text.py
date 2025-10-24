#!/usr/bin/env python3
"""
Compare actual text output between Docling configurations.

Exports full text from different configurations and compares character counts,
word counts, and actual content differences.
"""

from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import OcrMacOptions, PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption


def extract_all_text(doc) -> str:
    """Extract all text from document."""
    return "\n\n".join(item.text for item in doc.document.texts if hasattr(item, "text"))


def get_stats(text: str) -> dict:
    """Get text statistics."""
    return {
        "chars": len(text),
        "chars_no_whitespace": len(text.replace(" ", "").replace("\n", "").replace("\t", "")),
        "words": len(text.split()),
        "lines": len(text.split("\n")),
    }


def test_and_export(
    name: str, pipeline_options: PdfPipelineOptions, pdf_path: Path, output_dir: Path
):
    """Test configuration and export text."""
    print(f"\n{'=' * 80}")
    print(f"Config: {name}")
    print(f"{'=' * 80}")

    # Create converter
    converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}
    )

    # Convert
    doc = converter.convert(str(pdf_path))

    # Extract text
    text = extract_all_text(doc)

    # Get stats
    stats = get_stats(text)

    print(f"  Items: {len(doc.document.texts)}")
    print(f"  Characters: {stats['chars']:,}")
    print(f"  Characters (no whitespace): {stats['chars_no_whitespace']:,}")
    print(f"  Words: {stats['words']:,}")
    print(f"  Lines: {stats['lines']:,}")

    # Save text
    output_path = output_dir / f"{name}.txt"
    output_path.write_text(text, encoding="utf-8")
    print(f"  Saved: {output_path}")

    return text, stats


def main():
    """Compare default vs keep_empty_clusters configuration."""
    pdf_path = Path(
        "results/ocr_engine_comparison/academic_limbo__reforming_campus_speech_governance_for_students_image_only.pdf"
    )
    output_dir = Path("results/config_comparison")
    output_dir.mkdir(parents=True, exist_ok=True)

    if not pdf_path.exists():
        print(f"Error: {pdf_path} not found")
        return 1

    results = {}

    # Config 1: Default
    opts1 = PdfPipelineOptions()
    opts1.do_ocr = True
    opts1.ocr_options = OcrMacOptions()
    text1, stats1 = test_and_export("default", opts1, pdf_path, output_dir)
    results["default"] = (text1, stats1)

    # Config 2: Keep empty clusters
    opts2 = PdfPipelineOptions()
    opts2.do_ocr = True
    opts2.ocr_options = OcrMacOptions()
    opts2.layout_options.keep_empty_clusters = True
    text2, stats2 = test_and_export("keep_empty_clusters", opts2, pdf_path, output_dir)
    results["keep_empty_clusters"] = (text2, stats2)

    # Compare
    print(f"\n{'=' * 80}")
    print("COMPARISON")
    print(f"{'=' * 80}")

    char_diff = stats2["chars"] - stats1["chars"]
    char_nows_diff = stats2["chars_no_whitespace"] - stats1["chars_no_whitespace"]
    word_diff = stats2["words"] - stats1["words"]
    line_diff = stats2["lines"] - stats1["lines"]

    print(f"\nCharacter difference: {char_diff:+,} ({char_diff / stats1['chars'] * 100:+.2f}%)")
    print(
        f"Character difference (no whitespace): {char_nows_diff:+,} ({char_nows_diff / stats1['chars_no_whitespace'] * 100:+.2f}%)"
    )
    print(f"Word difference: {word_diff:+,} ({word_diff / stats1['words'] * 100:+.2f}%)")
    print(f"Line difference: {line_diff:+,}")

    # Find differences
    if text1 != text2:
        print("\n✓ Text content differs")
        print("\nCreating diff file...")

        # Simple line-by-line comparison
        lines1 = text1.split("\n")
        lines2 = text2.split("\n")

        diff_path = output_dir / "diff.txt"
        with open(diff_path, "w", encoding="utf-8") as f:
            f.write("Lines only in keep_empty_clusters:\n")
            f.write("=" * 80 + "\n\n")
            for line in lines2:
                if line and line not in text1:
                    f.write(f"+ {line}\n")

            f.write("\n\n")
            f.write("Lines only in default:\n")
            f.write("=" * 80 + "\n\n")
            for line in lines1:
                if line and line not in text2:
                    f.write(f"- {line}\n")

        print(f"Saved diff: {diff_path}")
    else:
        print("\n✗ Text content identical")

    print(f"\n✓ Text files saved to: {output_dir}")
    return 0


if __name__ == "__main__":
    exit(main())
