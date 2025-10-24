#!/usr/bin/env python3
"""
Compare OCR engines (ocrmac vs tesseract) against HTML ground truth.

Tests on worst-performing PDFs to identify specific word/character differences.
Focus: actual content differences (words/characters), not just symbols.
"""

import json
import re
import time
from pathlib import Path
from typing import Any

from docling_testing import create_image_only_pdf, create_ocr_converter


def load_ground_truth(json_path: Path) -> dict[str, list[str]]:
    """Load ground truth paragraphs from HTML extraction JSON."""
    with open(json_path) as f:
        data = json.load(f)

    # Extract body text and footnotes
    body_texts = []
    footnote_texts = []

    for para in data.get("paragraphs", []):
        text = para.get("text", "").strip()
        label = para.get("label", "")

        if text:
            if label == "body-text":
                body_texts.append(text)
            elif label == "footnote-text":
                footnote_texts.append(text)

    return {
        "body_text": body_texts,
        "footnote_text": footnote_texts,
        "all_text": body_texts + footnote_texts,
    }


def extract_docling_text(doc: Any) -> list[str]:
    """Extract all text blocks from Docling document."""
    texts = []

    if doc.document.texts:
        for item in doc.document.texts:
            if item.text:
                texts.append(item.text.strip())

    return texts


def extract_words(text_blocks: list[str]) -> set[str]:
    """Extract normalized word tokens (alphanumeric only)."""
    words = set()
    for block in text_blocks:
        # Extract alphanumeric sequences
        tokens = re.findall(r"\b[a-zA-Z0-9]+\b", block.lower())
        words.update(tokens)
    return words


def calculate_recall(extracted_words: set[str], ground_truth_words: set[str]) -> float:
    """Calculate word-level recall."""
    if not ground_truth_words:
        return 0.0
    matches = extracted_words & ground_truth_words
    return 100 * len(matches) / len(ground_truth_words)


def calculate_precision(extracted_words: set[str], ground_truth_words: set[str]) -> float:
    """Calculate word-level precision."""
    if not extracted_words:
        return 0.0
    matches = extracted_words & ground_truth_words
    return 100 * len(matches) / len(extracted_words)


def find_unique_words(set_a: set[str], set_b: set[str], limit: int = 20) -> list[str]:
    """Find words in set_a but not in set_b."""
    unique = set_a - set_b
    return sorted(unique)[:limit]


def run_ocr_comparison(
    pdf_name: str, pdf_path: Path, ground_truth_path: Path, output_dir: Path
) -> dict:
    """Run OCR comparison for a single PDF."""

    print(f"\n{'=' * 80}")
    print(f"Processing: {pdf_name}")
    print(f"{'=' * 80}")

    # Load ground truth
    print("\n[1/5] Loading ground truth...")
    gt_data = load_ground_truth(ground_truth_path)
    gt_words = extract_words(gt_data["all_text"])
    gt_body_words = extract_words(gt_data["body_text"])
    gt_footnote_words = extract_words(gt_data["footnote_text"])

    print(f"  Ground truth: {len(gt_words):,} unique words")
    print(f"    Body text: {len(gt_body_words):,} words")
    print(f"    Footnotes: {len(gt_footnote_words):,} words")

    # Create image-only PDF
    print("\n[2/5] Creating image-only PDF (300 DPI, grayscale)...")
    img_pdf_path = output_dir / f"{pdf_name}_image_only.pdf"
    create_image_only_pdf(pdf_path, img_pdf_path, dpi=300, grayscale=True)
    print(f"  Saved: {img_pdf_path}")

    # Run ocrmac
    print("\n[3/5] Running Docling with ocrmac...")
    start = time.time()
    ocrmac_converter = create_ocr_converter("ocrmac")
    ocrmac_doc = ocrmac_converter.convert(str(img_pdf_path))
    ocrmac_time = time.time() - start
    ocrmac_texts = extract_docling_text(ocrmac_doc)
    ocrmac_words = extract_words(ocrmac_texts)
    print(f"  Extracted: {len(ocrmac_words):,} unique words from {len(ocrmac_texts)} blocks")
    print(f"  Time: {ocrmac_time:.1f}s")

    # Run tesseract
    print("\n[4/5] Running Docling with tesseract...")
    start = time.time()
    tesseract_converter = create_ocr_converter("tesseract")
    tesseract_doc = tesseract_converter.convert(str(img_pdf_path))
    tesseract_time = time.time() - start
    tesseract_texts = extract_docling_text(tesseract_doc)
    tesseract_words = extract_words(tesseract_texts)
    print(f"  Extracted: {len(tesseract_words):,} unique words from {len(tesseract_texts)} blocks")
    print(f"  Time: {tesseract_time:.1f}s")

    # Calculate metrics
    print("\n[5/5] Calculating metrics...")

    # Ground truth comparison
    ocrmac_recall = calculate_recall(ocrmac_words, gt_words)
    ocrmac_precision = calculate_precision(ocrmac_words, gt_words)
    ocrmac_f1 = (
        2 * (ocrmac_precision * ocrmac_recall) / (ocrmac_precision + ocrmac_recall)
        if (ocrmac_precision + ocrmac_recall) > 0
        else 0
    )

    tesseract_recall = calculate_recall(tesseract_words, gt_words)
    tesseract_precision = calculate_precision(tesseract_words, gt_words)
    tesseract_f1 = (
        2 * (tesseract_precision * tesseract_recall) / (tesseract_precision + tesseract_recall)
        if (tesseract_precision + tesseract_recall) > 0
        else 0
    )

    # Engine comparison
    shared_words = ocrmac_words & tesseract_words
    only_ocrmac = ocrmac_words - tesseract_words
    only_tesseract = tesseract_words - ocrmac_words

    # Ground truth analysis
    gt_only_ocrmac = (ocrmac_words & gt_words) - (tesseract_words & gt_words)
    gt_only_tesseract = (tesseract_words & gt_words) - (ocrmac_words & gt_words)

    results = {
        "pdf_name": pdf_name,
        "ground_truth": {
            "total_words": len(gt_words),
            "body_words": len(gt_body_words),
            "footnote_words": len(gt_footnote_words),
        },
        "ocrmac": {
            "unique_words": len(ocrmac_words),
            "text_blocks": len(ocrmac_texts),
            "recall": ocrmac_recall,
            "precision": ocrmac_precision,
            "f1": ocrmac_f1,
            "time_s": ocrmac_time,
        },
        "tesseract": {
            "unique_words": len(tesseract_words),
            "text_blocks": len(tesseract_texts),
            "recall": tesseract_recall,
            "precision": tesseract_precision,
            "f1": tesseract_f1,
            "time_s": tesseract_time,
        },
        "comparison": {
            "shared_words": len(shared_words),
            "only_ocrmac": len(only_ocrmac),
            "only_tesseract": len(only_tesseract),
            "gt_only_ocrmac": len(gt_only_ocrmac),
            "gt_only_tesseract": len(gt_only_tesseract),
        },
        "examples": {
            "only_ocrmac": find_unique_words(only_ocrmac, tesseract_words, limit=30),
            "only_tesseract": find_unique_words(only_tesseract, ocrmac_words, limit=30),
            "gt_only_ocrmac": sorted(gt_only_ocrmac)[:30],
            "gt_only_tesseract": sorted(gt_only_tesseract)[:30],
        },
    }

    # Print summary
    print(f"\n{'=' * 80}")
    print(f"RESULTS: {pdf_name}")
    print(f"{'=' * 80}")
    print("\nGround Truth Coverage:")
    print(
        f"  ocrmac:    {ocrmac_recall:6.2f}% recall, {ocrmac_precision:6.2f}% precision, {ocrmac_f1:6.2f}% F1"
    )
    print(
        f"  tesseract: {tesseract_recall:6.2f}% recall, {tesseract_precision:6.2f}% precision, {tesseract_f1:6.2f}% F1"
    )

    print("\nEngine Comparison:")
    print(f"  Shared words:       {len(shared_words):,}")
    print(f"  Only in ocrmac:     {len(only_ocrmac):,}")
    print(f"  Only in tesseract:  {len(only_tesseract):,}")

    print("\nGround Truth Words Found by Only One Engine:")
    print(f"  ocrmac only:    {len(gt_only_ocrmac):,} words")
    print(f"  tesseract only: {len(gt_only_tesseract):,} words")

    if gt_only_ocrmac:
        print(f"\n  Examples (ocrmac only): {', '.join(sorted(gt_only_ocrmac)[:10])}")
    if gt_only_tesseract:
        print(f"  Examples (tesseract only): {', '.join(sorted(gt_only_tesseract)[:10])}")

    # Save results
    results_path = output_dir / f"{pdf_name}_comparison.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved: {results_path}")

    return results


def main():
    """Run OCR comparison on worst-performing PDFs."""

    # Define worst performers
    test_pdfs = [
        "usc_law_review_listening_on_campus_academic_freedom_and_its_audiences",  # 4.94%
        "texas_law_review_working-with-statutes",  # 17.79%
        "california_law_review_amazon-trademark",  # 20.27%
        "antitrusts_interdependence_paradox",  # 20.52%
        "ucla_law_review_insurgent_knowledge_battling_cdcr_from_inside_the_system_the_story_of_the_essential_collaboration_be",  # 23.88%
    ]

    pdf_dir = Path("data/v3_data/raw_pdf")
    gt_dir = Path("data/v3_data/processed_html")
    output_dir = Path("results/ocr_engine_comparison")
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("OCR ENGINE COMPARISON: ocrmac vs tesseract")
    print("=" * 80)
    print(f"\nTesting {len(test_pdfs)} worst-performing PDFs")
    print(f"Output directory: {output_dir}")

    all_results = []

    for i, pdf_name in enumerate(test_pdfs, 1):
        pdf_path = pdf_dir / f"{pdf_name}.pdf"
        gt_path = gt_dir / f"{pdf_name}.json"

        if not pdf_path.exists():
            print(f"\n[{i}/{len(test_pdfs)}] SKIP: PDF not found: {pdf_name}")
            continue

        if not gt_path.exists():
            print(f"\n[{i}/{len(test_pdfs)}] SKIP: Ground truth not found: {pdf_name}")
            continue

        print(f"\n[{i}/{len(test_pdfs)}] Testing: {pdf_name}")

        try:
            results = run_ocr_comparison(pdf_name, pdf_path, gt_path, output_dir)
            all_results.append(results)
        except Exception as e:
            print(f"\nERROR processing {pdf_name}: {e}")
            import traceback

            traceback.print_exc()
            continue

    # Generate summary
    print(f"\n{'=' * 80}")
    print("AGGREGATE SUMMARY")
    print(f"{'=' * 80}")

    if all_results:
        print(f"\nTested {len(all_results)} PDFs:")
        print(f"\n{'PDF':<50} {'ocrmac Recall':<15} {'tesseract Recall':<15} {'Winner'}")
        print("-" * 95)

        for r in all_results:
            ocr_recall = r["ocrmac"]["recall"]
            tess_recall = r["tesseract"]["recall"]
            winner = (
                "ocrmac"
                if ocr_recall > tess_recall
                else "tesseract"
                if tess_recall > ocr_recall
                else "tie"
            )
            pdf_short = r["pdf_name"][:48]
            print(f"{pdf_short:<50} {ocr_recall:6.2f}%        {tess_recall:6.2f}%        {winner}")

        # Save summary
        summary_path = output_dir / "summary.json"
        with open(summary_path, "w") as f:
            json.dump(all_results, f, indent=2)
        print(f"\nSummary saved: {summary_path}")
    else:
        print("\nNo results to summarize.")

    print(f"\n{'=' * 80}")
    print("COMPARISON COMPLETE")
    print(f"{'=' * 80}")


if __name__ == "__main__":
    main()
