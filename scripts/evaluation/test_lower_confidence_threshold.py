#!/usr/bin/env python3
"""
Test lowering layout model confidence threshold to capture more text.

The layout model filters out bounding boxes with confidence < 0.3 (default).
This script tests whether lowering the threshold captures missing TOC text.
"""

from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import OcrMacOptions, PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption


def monkey_patch_layout_predictor(threshold=0.1):
    """
    Monkey-patch LayoutPredictor to use a custom confidence threshold.

    WARNING: This is a hack that directly modifies Docling's internal behavior.
    """
    from docling_ibm_models.layoutmodel import layout_predictor

    original_init = layout_predictor.LayoutPredictor.__init__

    def patched_init(self, artifact_path, device="cpu", num_threads=4, **kwargs):
        # Force our custom threshold, ignore any passed base_threshold
        print(f"✓ LayoutPredictor patched: base_threshold={threshold} (was 0.3)")
        original_init(
            self,
            artifact_path=artifact_path,
            device=device,
            num_threads=num_threads,
            base_threshold=threshold,  # Custom threshold
            blacklist_classes=set(),
        )

    layout_predictor.LayoutPredictor.__init__ = patched_init


def extract_text(doc):
    """Extract all text from document."""
    return "\n\n".join(item.text for item in doc.document.texts if hasattr(item, "text"))


def get_stats(text: str) -> dict:
    """Get text statistics."""
    return {
        "chars": len(text),
        "chars_no_ws": len(text.replace(" ", "").replace("\n", "").replace("\t", "")),
        "words": len(text.split()),
        "lines": len(text.split("\n")),
    }


def main():
    """Test lower confidence threshold on academic_limbo."""
    pdf_path = Path(
        "results/ocr_engine_comparison/academic_limbo__reforming_campus_speech_governance_for_students_image_only.pdf"
    )
    output_dir = Path("results/threshold_test")
    output_dir.mkdir(parents=True, exist_ok=True)

    if not pdf_path.exists():
        print(f"Error: {pdf_path} not found")
        return 1

    results = {}

    # Test 1: Default threshold (0.3)
    print("\n" + "=" * 80)
    print("TEST 1: DEFAULT THRESHOLD (0.3)")
    print("=" * 80)

    opts1 = PdfPipelineOptions()
    opts1.do_ocr = True
    opts1.ocr_options = OcrMacOptions()

    converter1 = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts1)}
    )

    doc1 = converter1.convert(str(pdf_path))
    text1 = extract_text(doc1)
    stats1 = get_stats(text1)

    print(f"  Items: {len(doc1.document.texts)}")
    print(f"  Characters: {stats1['chars']:,}")
    print(f"  Words: {stats1['words']:,}")

    (output_dir / "default_0.3.txt").write_text(text1, encoding="utf-8")
    results["default"] = stats1

    # Test 2: Lower threshold (0.1) - PATCHED
    print("\n" + "=" * 80)
    print("TEST 2: LOWER THRESHOLD (0.1) - MONKEY PATCHED")
    print("=" * 80)

    # Apply monkey patch
    monkey_patch_layout_predictor(threshold=0.1)

    opts2 = PdfPipelineOptions()
    opts2.do_ocr = True
    opts2.ocr_options = OcrMacOptions()

    converter2 = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts2)}
    )

    doc2 = converter2.convert(str(pdf_path))
    text2 = extract_text(doc2)
    stats2 = get_stats(text2)

    print(f"  Items: {len(doc2.document.texts)}")
    print(f"  Characters: {stats2['chars']:,}")
    print(f"  Words: {stats2['words']:,}")

    (output_dir / "lower_0.1.txt").write_text(text2, encoding="utf-8")
    results["lower"] = stats2

    # Compare
    print("\n" + "=" * 80)
    print("COMPARISON")
    print("=" * 80)

    char_diff = stats2["chars"] - stats1["chars"]
    word_diff = stats2["words"] - stats1["words"]

    print("\nText GAINED with lower threshold:")
    print(f"  Characters: {char_diff:+,} ({char_diff / stats1['chars'] * 100:+.2f}%)")
    print(f"  Words: {word_diff:+,} ({word_diff / stats1['words'] * 100:+.2f}%)")

    if word_diff > 0:
        # Find new lines
        lines1 = set(text1.split("\n"))
        lines2 = set(text2.split("\n"))
        new_lines = lines2 - lines1

        print(f"\n{len(new_lines)} new lines captured!")
        print("\nFirst 20 new lines:")
        for i, line in enumerate(sorted(new_lines)[:20], 1):
            print(f"  {i}. {line[:80]}{'...' if len(line) > 80 else ''}")

        # Save diff
        (output_dir / "new_lines.txt").write_text("\n".join(sorted(new_lines)), encoding="utf-8")

    print(f"\n✓ Results saved to: {output_dir}")
    return 0


if __name__ == "__main__":
    exit(main())
