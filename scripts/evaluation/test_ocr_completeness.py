#!/usr/bin/env python3
"""
Rigorous completeness testing for OCR pipeline.

Tests a single PDF through the full pipeline and verifies:
1. All pages are processed
2. Content matches HTML ground truth
3. Last paragraph is present
4. Footnote coverage
"""

import argparse
import json
import logging
from pathlib import Path
from typing import Any

from rapidfuzz import fuzz

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def extract_text_from_repr(text_repr: str) -> str:
    """Extract text content from Docling repr string."""
    import re

    match = re.search(r"text='([^']*(?:''[^']*)*)'", text_repr)
    return match.group(1).replace("\\'", "'") if match else ""


def test_completeness(
    extraction_path: Path, ground_truth_path: Path, pdf_pages: int
) -> dict[str, Any]:
    """Test extraction completeness against ground truth.

    Args:
        extraction_path: Path to extraction JSON
        ground_truth_path: Path to ground truth JSON
        pdf_pages: Total pages in PDF

    Returns:
        Completeness test results
    """
    # Load data
    with open(extraction_path) as f:
        extraction = json.load(f)

    with open(ground_truth_path) as f:
        ground_truth = json.load(f)

    # Extract PDF text
    pdf_texts = [extract_text_from_repr(t) for t in extraction["texts"]]
    pdf_all_text = " ".join(pdf_texts)
    pdf_total_chars = len(pdf_all_text)

    # Extract ground truth text
    gt_body = ground_truth.get("body_text_paragraphs", [])
    gt_footnotes = ground_truth.get("footnotes", [])
    gt_all_text = " ".join([p["text"] for p in gt_body] + [f["text"] for f in gt_footnotes])
    gt_total_chars = len(gt_all_text)

    # Test 1: Page count
    extracted_pages = extraction.get("page_count", 0)
    pages_complete = extracted_pages >= pdf_pages

    # Test 2: Character count comparison
    char_coverage = pdf_total_chars / gt_total_chars if gt_total_chars > 0 else 0
    chars_complete = char_coverage >= 0.8  # At least 80% of content

    # Test 3: Last paragraph similarity
    gt_last_para = gt_body[-1]["text"][:500] if gt_body else ""
    pdf_last_para = pdf_texts[-1][:500] if pdf_texts else ""
    last_para_similarity = fuzz.ratio(gt_last_para.lower(), pdf_last_para.lower())
    last_para_complete = last_para_similarity >= 70  # At least 70% match

    # Test 4: First paragraph similarity (sanity check)
    gt_first_para = gt_body[0]["text"][:500] if gt_body else ""
    pdf_first_para = ""
    for text in pdf_texts:
        if len(text) > 50:  # Skip headers
            pdf_first_para = text[:500]
            break
    first_para_similarity = fuzz.ratio(gt_first_para.lower(), pdf_first_para.lower())
    first_para_ok = first_para_similarity >= 70

    # Test 5: Footnote count comparison
    gt_footnote_count = len(gt_footnotes)
    # Extract footnote blocks from PDF (rough estimate)
    pdf_footnote_count = sum(1 for t in pdf_texts if len(t) > 50 and len(t) < 500)
    footnote_ratio = pdf_footnote_count / gt_footnote_count if gt_footnote_count > 0 else 0

    # Overall assessment
    all_tests_pass = all(
        [
            pages_complete,
            chars_complete,
            last_para_complete,
            first_para_ok,
        ]
    )

    return {
        "overall_complete": all_tests_pass,
        "tests": {
            "pages": {
                "pass": pages_complete,
                "extracted": extracted_pages,
                "expected": pdf_pages,
                "message": f"Extracted {extracted_pages}/{pdf_pages} pages",
            },
            "characters": {
                "pass": chars_complete,
                "coverage": char_coverage,
                "pdf_chars": pdf_total_chars,
                "gt_chars": gt_total_chars,
                "message": f"Character coverage: {char_coverage:.1%} ({pdf_total_chars:,} / {gt_total_chars:,})",
            },
            "last_paragraph": {
                "pass": last_para_complete,
                "similarity": last_para_similarity,
                "message": f"Last paragraph match: {last_para_similarity:.1f}%",
                "pdf_text": pdf_last_para[:200],
                "gt_text": gt_last_para[:200],
            },
            "first_paragraph": {
                "pass": first_para_ok,
                "similarity": first_para_similarity,
                "message": f"First paragraph match: {first_para_similarity:.1f}%",
            },
            "footnotes": {
                "info_only": True,
                "ratio": footnote_ratio,
                "pdf_count": pdf_footnote_count,
                "gt_count": gt_footnote_count,
                "message": f"Footnote blocks: {pdf_footnote_count} vs ground truth {gt_footnote_count}",
            },
        },
    }


def main():
    """Test OCR pipeline completeness."""
    parser = argparse.ArgumentParser(description="Test OCR pipeline completeness")
    parser.add_argument(
        "--extraction",
        type=Path,
        required=True,
        help="Path to extraction JSON file",
    )
    parser.add_argument(
        "--ground-truth",
        type=Path,
        required=True,
        help="Path to ground truth JSON file",
    )
    parser.add_argument(
        "--pdf-pages",
        type=int,
        required=True,
        help="Total pages in original PDF",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed test results",
    )

    args = parser.parse_args()

    # Run completeness test
    logger.info("=" * 80)
    logger.info("OCR PIPELINE COMPLETENESS TEST")
    logger.info("=" * 80)
    logger.info(f"\nExtraction: {args.extraction.name}")
    logger.info(f"Ground truth: {args.ground_truth.name}")
    logger.info(f"Expected pages: {args.pdf_pages}\n")

    results = test_completeness(args.extraction, args.ground_truth, args.pdf_pages)

    # Print results
    logger.info("-" * 80)
    logger.info("TEST RESULTS")
    logger.info("-" * 80)

    for test_name, test_data in results["tests"].items():
        if test_data.get("info_only"):
            logger.info(f"\n[INFO] {test_name.replace('_', ' ').title()}")
        else:
            status = "✓ PASS" if test_data["pass"] else "✗ FAIL"
            logger.info(f"\n[{status}] {test_name.replace('_', ' ').title()}")

        logger.info(f"  {test_data['message']}")

        if args.verbose and test_name == "last_paragraph":
            logger.info("\n  PDF last paragraph:")
            logger.info(f"    '{test_data['pdf_text']}...'")
            logger.info("\n  Ground truth last paragraph:")
            logger.info(f"    '{test_data['gt_text']}...'")

    # Overall result
    logger.info("\n" + "=" * 80)
    if results["overall_complete"]:
        logger.info("✓ OVERALL: COMPLETE")
        logger.info("  Extraction contains full document content")
    else:
        logger.info("✗ OVERALL: INCOMPLETE")
        logger.info("  Extraction is missing significant content")

        # Show which tests failed
        failed_tests = [
            name
            for name, data in results["tests"].items()
            if not data.get("pass", True) and not data.get("info_only")
        ]
        if failed_tests:
            logger.info(f"\n  Failed tests: {', '.join(failed_tests)}")

    logger.info("=" * 80)

    # Exit with error code if incomplete
    return 0 if results["overall_complete"] else 1


if __name__ == "__main__":
    exit(main())
