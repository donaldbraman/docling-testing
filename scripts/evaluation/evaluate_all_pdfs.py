#!/usr/bin/env python3
"""
Evaluate sequence alignment across all PDFs with ground truth.

Runs baseline algorithm on each PDF and reports F1 scores.

Usage:
    python scripts/evaluation/evaluate_all_pdfs.py [--threshold THRESHOLD]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))

from fuzzy_matcher import match_all_lines_with_locality
from parse_extraction import ExtractedItem
from prepare_matching_data import load_html_ground_truth
from sequence_alignment.alignment_metrics import calculate_metrics


def extract_line_level_items(pdf_path: Path) -> list:
    """Extract line-level text from PDF as ExtractedItem objects."""
    import fitz

    doc = fitz.open(pdf_path)
    items = []

    for page_idx, page in enumerate(doc):
        page_num = page_idx + 1
        blocks = page.get_text("dict")["blocks"]

        for block in blocks:
            if "lines" not in block:
                continue

            for line in block["lines"]:
                text = " ".join([span["text"] for span in line["spans"]])
                bbox = line["bbox"]

                if text.strip():
                    items.append(
                        ExtractedItem(
                            text=text.strip(),
                            label="TEXT",
                            page_num=page_num,
                            bbox=bbox,
                            original_docling_label="DocItemLabel.TEXT",
                        )
                    )

    doc.close()
    return items


def evaluate_single_pdf(pdf_name: str, pdf_path: Path, threshold: float) -> dict:
    """
    Evaluate sequence alignment on a single PDF.

    Returns:
        Dictionary with metrics
    """
    # Extract line-level items
    items = extract_line_level_items(pdf_path)

    # Load ground truth
    try:
        body_html, footnote_html = load_html_ground_truth(pdf_name)
    except FileNotFoundError:
        return None

    # Run baseline algorithm
    class BaselineMatch:
        def __init__(self, fuzzy_match):
            self.extraction_item = fuzzy_match.extraction_item
            self.matched_html = fuzzy_match.matched_html
            self.similarity_score = fuzzy_match.similarity_score
            self.corrected_label = fuzzy_match.corrected_label
            if fuzzy_match.corrected_label == "body-text":
                self.assignment = "body"
            elif fuzzy_match.corrected_label == "footnote-text":
                self.assignment = "footnote"
            else:
                self.assignment = "original"

    matches = match_all_lines_with_locality(items, body_html, footnote_html, threshold)
    matches = [BaselineMatch(m) for m in matches]

    # Calculate metrics
    metrics = calculate_metrics(matches, body_html, footnote_html)

    return {
        "pdf_name": pdf_name,
        "num_lines": len(items),
        "body_html_count": len(body_html),
        "footnote_html_count": len(footnote_html),
        "body_f1": metrics.body_f1,
        "body_precision": metrics.body_precision,
        "body_recall": metrics.body_recall,
        "footnote_f1": metrics.footnote_f1,
        "footnote_precision": metrics.footnote_precision,
        "footnote_recall": metrics.footnote_recall,
        "macro_f1": metrics.macro_f1,
    }


def main():
    """Run evaluation across all PDFs."""
    parser = argparse.ArgumentParser(description="Evaluate all PDFs with ground truth")
    parser.add_argument(
        "--threshold", type=float, default=0.3, help="Similarity threshold (default: 0.3)"
    )
    args = parser.parse_args()

    print("=" * 80)
    print("EVALUATING ALL PDFs WITH GROUND TRUTH")
    print("=" * 80)
    print(f"\nThreshold: {args.threshold}")
    print("Algorithm: Baseline (locality-aware fuzzy matching)")

    # Find all ground truth files
    gt_dir = Path("data/v3_data/processed_html")
    gt_files = sorted(gt_dir.glob("*.json"))

    print(f"\nFound {len(gt_files)} PDFs with ground truth")

    # Find corresponding PDFs
    pdf_dirs = [Path("data/v3_data/raw_pdf"), Path("data/raw_pdf")]

    results = []
    skipped = []

    print("\n" + "=" * 80)
    print("RUNNING EVALUATIONS")
    print("=" * 80)

    for i, gt_file in enumerate(gt_files, 1):
        pdf_name = gt_file.stem

        # Find PDF file
        pdf_path = None
        for pdf_dir in pdf_dirs:
            candidate = pdf_dir / f"{pdf_name}.pdf"
            if candidate.exists():
                pdf_path = candidate
                break

        if not pdf_path:
            print(f"\n[{i}/{len(gt_files)}] ⚠️  {pdf_name}")
            print("  PDF not found, skipping")
            skipped.append(pdf_name)
            continue

        try:
            print(f"\n[{i}/{len(gt_files)}] 📄 {pdf_name}")
            result = evaluate_single_pdf(pdf_name, pdf_path, args.threshold)

            if result is None:
                print("  ⚠️  Ground truth load failed, skipping")
                skipped.append(pdf_name)
                continue

            results.append(result)

            # Print results
            print(
                f"  Lines: {result['num_lines']:4d} | "
                f"Body GT: {result['body_html_count']:2d} | "
                f"Footnote GT: {result['footnote_html_count']:2d}"
            )
            print(
                f"  Body F1: {result['body_f1']:.3f} | "
                f"Footnote F1: {result['footnote_f1']:.3f} | "
                f"Macro F1: {result['macro_f1']:.3f}"
            )
            sys.stdout.flush()  # Flush output immediately

        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
            skipped.append(pdf_name)
            continue

    # Summary statistics
    print("\n" + "=" * 80)
    print("SUMMARY STATISTICS")
    print("=" * 80)

    if results:
        df = pd.DataFrame(results)

        print(f"\n✅ Successfully evaluated: {len(results)} PDFs")
        print(f"⚠️  Skipped: {len(skipped)} PDFs")

        print("\n📊 Macro F1 Statistics:")
        print(f"  Mean:   {df['macro_f1'].mean():.3f}")
        print(f"  Median: {df['macro_f1'].median():.3f}")
        print(f"  Std:    {df['macro_f1'].std():.3f}")
        print(f"  Min:    {df['macro_f1'].min():.3f}")
        print(f"  Max:    {df['macro_f1'].max():.3f}")

        print("\n📊 Body F1 Statistics:")
        print(f"  Mean:   {df['body_f1'].mean():.3f}")
        print(f"  Median: {df['body_f1'].median():.3f}")
        print(f"  Std:    {df['body_f1'].std():.3f}")
        print(f"  Min:    {df['body_f1'].min():.3f}")
        print(f"  Max:    {df['body_f1'].max():.3f}")

        print("\n📊 Footnote F1 Statistics:")
        print(f"  Mean:   {df['footnote_f1'].mean():.3f}")
        print(f"  Median: {df['footnote_f1'].median():.3f}")
        print(f"  Std:    {df['footnote_f1'].std():.3f}")
        print(f"  Min:    {df['footnote_f1'].min():.3f}")
        print(f"  Max:    {df['footnote_f1'].max():.3f}")

        # Distribution of performance
        print("\n📊 Performance Distribution (Macro F1):")
        perfect = len(df[df["macro_f1"] == 1.0])
        excellent = len(df[(df["macro_f1"] >= 0.95) & (df["macro_f1"] < 1.0)])
        good = len(df[(df["macro_f1"] >= 0.8) & (df["macro_f1"] < 0.95)])
        fair = len(df[(df["macro_f1"] >= 0.6) & (df["macro_f1"] < 0.8)])
        poor = len(df[df["macro_f1"] < 0.6])

        print(f"  Perfect (1.00):       {perfect:3d} ({perfect / len(df) * 100:.1f}%)")
        print(f"  Excellent (0.95-1.00): {excellent:3d} ({excellent / len(df) * 100:.1f}%)")
        print(f"  Good (0.80-0.95):      {good:3d} ({good / len(df) * 100:.1f}%)")
        print(f"  Fair (0.60-0.80):      {fair:3d} ({fair / len(df) * 100:.1f}%)")
        print(f"  Poor (<0.60):          {poor:3d} ({poor / len(df) * 100:.1f}%)")

        # Worst performing PDFs
        if poor > 0 or fair > 0:
            print("\n📊 Lowest Performing PDFs (for investigation):")
            worst = df.nsmallest(10, "macro_f1")[["pdf_name", "macro_f1", "body_f1", "footnote_f1"]]
            for _, row in worst.iterrows():
                print(
                    f"  {row['pdf_name'][:60]:60s} | Macro: {row['macro_f1']:.3f} | "
                    f"Body: {row['body_f1']:.3f} | Footnote: {row['footnote_f1']:.3f}"
                )

        # Save results
        output_dir = Path("results/sequence_alignment/full_evaluation")
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save detailed results
        df.to_csv(output_dir / "all_pdfs_results.csv", index=False)
        print(f"\n💾 Saved detailed results to {output_dir}/all_pdfs_results.csv")

        # Save summary JSON
        summary = {
            "threshold": args.threshold,
            "total_pdfs": len(results),
            "skipped_pdfs": len(skipped),
            "mean_macro_f1": float(df["macro_f1"].mean()),
            "median_macro_f1": float(df["macro_f1"].median()),
            "mean_body_f1": float(df["body_f1"].mean()),
            "mean_footnote_f1": float(df["footnote_f1"].mean()),
            "perfect_count": int(perfect),
            "excellent_count": int(excellent),
            "good_count": int(good),
            "fair_count": int(fair),
            "poor_count": int(poor),
        }

        with open(output_dir / "summary.json", "w") as f:
            json.dump(summary, f, indent=2)
        print(f"💾 Saved summary to {output_dir}/summary.json")

    else:
        print("\n❌ No PDFs successfully evaluated")

    print("\n" + "=" * 80)
    print("EVALUATION COMPLETE")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    exit(main())
