#!/usr/bin/env python3
"""Analyze character-level differences between OCR engines."""

import json
import re
from pathlib import Path


def load_ground_truth(json_path: Path) -> str:
    """Load ground truth text."""
    with open(json_path) as f:
        data = json.load(f)

    texts = []
    for para in data.get("paragraphs", []):
        text = para.get("text", "").strip()
        if text:
            texts.append(text)

    return " ".join(texts)


def extract_docling_text(image_pdf: Path, engine: str) -> str:
    """Extract all text from Docling processing."""
    from docling_testing import create_ocr_converter

    converter = create_ocr_converter(engine)
    doc = converter.convert(str(image_pdf))

    texts = []
    if doc.document.texts:
        for item in doc.document.texts:
            if item.text:
                texts.append(item.text.strip())

    return " ".join(texts)


def get_character_stats(text: str) -> dict:
    """Get detailed character statistics."""

    # All characters
    total_chars = len(text)

    # Alphanumeric
    alphanumeric = len(re.findall(r"[a-zA-Z0-9]", text))

    # Letters only
    letters = len(re.findall(r"[a-zA-Z]", text))

    # Digits only
    digits = len(re.findall(r"[0-9]", text))

    # Whitespace
    whitespace = len(re.findall(r"\s", text))

    # Punctuation and symbols
    other = total_chars - alphanumeric - whitespace

    return {
        "total_chars": total_chars,
        "alphanumeric": alphanumeric,
        "letters": letters,
        "digits": digits,
        "whitespace": whitespace,
        "punctuation_symbols": other,
    }


def calculate_char_recall(extracted: str, ground_truth: str) -> float:
    """Calculate character-level recall."""
    # Normalize to lowercase for comparison
    ext_lower = extracted.lower()
    gt_lower = ground_truth.lower()

    # Count matching characters
    matches = 0
    for char in gt_lower:
        if char.isalnum() and char in ext_lower:
            matches += 1
            # Remove matched char to avoid double counting
            ext_lower = ext_lower.replace(char, "", 1)

    gt_alnum = sum(1 for c in gt_lower if c.isalnum())

    if gt_alnum == 0:
        return 0.0

    return 100 * matches / gt_alnum


def main():
    """Analyze character counts for all tested PDFs."""

    pdf_dir = Path("data/v3_data/raw_pdf")
    gt_dir = Path("data/v3_data/processed_html")
    ocr_dir = Path("results/ocr_engine_comparison")

    test_pdfs = [
        "usc_law_review_listening_on_campus_academic_freedom_and_its_audiences",
        "texas_law_review_working-with-statutes",
        "california_law_review_amazon-trademark",
        "antitrusts_interdependence_paradox",
        "ucla_law_review_insurgent_knowledge_battling_cdcr_from_inside_the_system_the_story_of_the_essential_collaboration_be",
    ]

    print("=" * 100)
    print("CHARACTER-LEVEL OCR ENGINE COMPARISON")
    print("=" * 100)

    results = []

    for i, pdf_name in enumerate(test_pdfs, 1):
        print(f"\n[{i}/5] {pdf_name[:60]}...")
        print("-" * 100)

        gt_path = gt_dir / f"{pdf_name}.json"
        image_pdf = ocr_dir / f"{pdf_name}_image_only.pdf"

        if not gt_path.exists() or not image_pdf.exists():
            print("  ⚠️  Files not found")
            continue

        # Load ground truth
        print("  Loading ground truth...")
        gt_text = load_ground_truth(gt_path)
        gt_stats = get_character_stats(gt_text)

        # Extract with both engines
        print("  Extracting with ocrmac...")
        ocrmac_text = extract_docling_text(image_pdf, "ocrmac")
        ocrmac_stats = get_character_stats(ocrmac_text)

        print("  Extracting with tesseract...")
        tesseract_text = extract_docling_text(image_pdf, "tesseract")
        tesseract_stats = get_character_stats(tesseract_text)

        # Calculate recall
        ocrmac_recall = calculate_char_recall(ocrmac_text, gt_text)
        tesseract_recall = calculate_char_recall(tesseract_text, gt_text)

        # Display results
        print("\n  Ground Truth:")
        print(f"    Total chars:    {gt_stats['total_chars']:,}")
        print(f"    Alphanumeric:   {gt_stats['alphanumeric']:,}")
        print(f"    Letters:        {gt_stats['letters']:,}")
        print(f"    Digits:         {gt_stats['digits']:,}")

        print("\n  ocrmac:")
        print(
            f"    Total chars:    {ocrmac_stats['total_chars']:,} ({100 * ocrmac_stats['total_chars'] / gt_stats['total_chars']:.1f}% of GT)"
        )
        print(
            f"    Alphanumeric:   {ocrmac_stats['alphanumeric']:,} ({100 * ocrmac_stats['alphanumeric'] / gt_stats['alphanumeric']:.1f}% of GT)"
        )
        print(f"    Letters:        {ocrmac_stats['letters']:,}")
        print(f"    Digits:         {ocrmac_stats['digits']:,}")
        print(f"    Char recall:    {ocrmac_recall:.2f}%")

        print("\n  tesseract:")
        print(
            f"    Total chars:    {tesseract_stats['total_chars']:,} ({100 * tesseract_stats['total_chars'] / gt_stats['total_chars']:.1f}% of GT)"
        )
        print(
            f"    Alphanumeric:   {tesseract_stats['alphanumeric']:,} ({100 * tesseract_stats['alphanumeric'] / gt_stats['alphanumeric']:.1f}% of GT)"
        )
        print(f"    Letters:        {tesseract_stats['letters']:,}")
        print(f"    Digits:         {tesseract_stats['digits']:,}")
        print(f"    Char recall:    {tesseract_recall:.2f}%")

        print("\n  Comparison:")
        print(
            f"    Char diff:      {tesseract_stats['total_chars'] - ocrmac_stats['total_chars']:,} chars (tesseract - ocrmac)"
        )
        print(
            f"    Winner:         {'tesseract' if tesseract_recall > ocrmac_recall else 'ocrmac'} ({abs(tesseract_recall - ocrmac_recall):.2f}% better)"
        )

        results.append(
            {
                "pdf_name": pdf_name,
                "ground_truth": gt_stats,
                "ocrmac": {**ocrmac_stats, "recall": ocrmac_recall},
                "tesseract": {**tesseract_stats, "recall": tesseract_recall},
            }
        )

    # Save results
    output_path = ocr_dir / "character_comparison.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    print("\n" + "=" * 100)
    print("CHARACTER COMPARISON COMPLETE")
    print("=" * 100)
    print(f"\nResults saved: {output_path}")

    # Summary table
    print("\n" + "=" * 100)
    print("SUMMARY TABLE")
    print("=" * 100)
    print(f"\n{'PDF':<65} {'ocrmac':>12} {'tesseract':>12} {'Winner':>10}")
    print("-" * 100)
    for r in results:
        name = r["pdf_name"][:60] + "..." if len(r["pdf_name"]) > 60 else r["pdf_name"]
        ocr_recall = r["ocrmac"]["recall"]
        tes_recall = r["tesseract"]["recall"]
        winner = "tesseract" if tes_recall > ocr_recall else "ocrmac"
        print(f"{name:<65} {ocr_recall:>11.2f}% {tes_recall:>11.2f}% {winner:>10}")


if __name__ == "__main__":
    main()
