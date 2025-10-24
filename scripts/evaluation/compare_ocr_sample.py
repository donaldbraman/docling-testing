#!/usr/bin/env python3
"""
Run OCR comparison on a diverse sample to identify recall patterns.

This script tests PDFs from different law reviews to:
1. Find any other magazine-style documents (low recall ~30%)
2. Identify middling performers (70-85% recall)
3. Validate that traditional articles achieve high recall (90%+)
"""

from pathlib import Path

from compare_ocr_with_ground_truth import run_ocr_comparison


def main():
    """Run OCR comparison on diverse sample."""

    # Select diverse sample: different law reviews and standalone titles
    test_pdfs = [
        # BU Law Review (middle tier)
        "bu_law_review_law_and_culture",
        "bu_law_review_learning_from_history",
        "bu_law_review_nil_compliance",
        # California Law Review (already tested amazon-trademark, test others)
        "california_law_review_affirmative-asylum",
        "california_law_review_judiciary-ada",
        # Michigan Law Review (top tier)
        "michigan_law_review_law_enforcement_privilege",
        "michigan_law_review_spending_clause_standing",
        # Standalone titles (various)
        "academic_limbo__reforming_campus_speech_governance_for_students",
        "policing_campus_protest",
        "overbroad_protest_laws",
    ]

    pdf_dir = Path("data/v3_data/raw_pdf")
    gt_dir = Path("data/v3_data/processed_html")
    output_dir = Path("results/ocr_engine_comparison")
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("OCR RECALL SCREENING - Diverse Sample")
    print("=" * 80)
    print(f"\nTesting {len(test_pdfs)} PDFs from different law reviews")
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

    # Generate summary sorted by recall
    print(f"\n{'=' * 80}")
    print("SUMMARY - Sorted by ocrmac Recall")
    print(f"{'=' * 80}")

    if all_results:
        # Sort by ocrmac recall
        sorted_results = sorted(all_results, key=lambda x: x["ocrmac"]["recall"])

        print(f"\n{'Recall':<10} {'PDF':<60}")
        print("-" * 70)

        for r in sorted_results:
            recall = r["ocrmac"]["recall"]
            pdf_short = r["pdf_name"][:58]

            # Color code by recall
            if recall < 40:
                category = "❌ LOW "
            elif recall < 85:
                category = "⚠️  MID "
            else:
                category = "✅ HIGH"

            print(f"{category} {recall:5.1f}%  {pdf_short}")

        print(f"\n{'=' * 80}")
        print("Recall Categories:")
        print("  ✅ HIGH (90%+):   Traditional academic articles")
        print("  ⚠️  MID (70-85%): Investigate for issues")
        print("  ❌ LOW (<40%):    Magazine-style, exclude from training")
        print(f"{'=' * 80}")

    else:
        print("\nNo results to summarize.")

    print(f"\n{'=' * 80}")
    print("SCREENING COMPLETE")
    print(f"{'=' * 80}")


if __name__ == "__main__":
    main()
