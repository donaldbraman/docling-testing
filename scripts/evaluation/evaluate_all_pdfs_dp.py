#!/usr/bin/env python3
"""
Evaluate all PDFs using DP two-sequence alignment.

This runs the computationally expensive DP algorithm on all 73 PDFs.
Expected runtime: 6-8 hours for all documents.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

from parse_extraction import ExtractedItem
from prepare_matching_data import load_html_ground_truth
from sequence_alignment.dp_alignment import dp_two_sequence_alignment


def extract_line_level_items(pdf_path: Path) -> list[ExtractedItem]:
    """Extract line-level text from PDF."""
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


def calculate_metrics(matches, body_html, footnote_html):
    """Calculate precision, recall, F1 for body and footnote."""
    body_html_texts = {h.text for h in body_html}
    footnote_html_texts = {h.text for h in footnote_html}

    # Body metrics
    body_tp = sum(
        1
        for m in matches
        if m.matched_html and m.matched_html.text in body_html_texts and m.assignment == "body"
    )
    body_fp = sum(
        1
        for m in matches
        if m.matched_html and m.matched_html.text in footnote_html_texts and m.assignment == "body"
    )
    body_fn = len(body_html) - body_tp

    body_precision = body_tp / (body_tp + body_fp) if (body_tp + body_fp) > 0 else 0.0
    body_recall = body_tp / (body_tp + body_fn) if (body_tp + body_fn) > 0 else 0.0
    body_f1 = (
        2 * (body_precision * body_recall) / (body_precision + body_recall)
        if (body_precision + body_recall) > 0
        else 0.0
    )

    # Footnote metrics
    footnote_tp = sum(
        1
        for m in matches
        if m.matched_html
        and m.matched_html.text in footnote_html_texts
        and m.assignment == "footnote"
    )
    footnote_fp = sum(
        1
        for m in matches
        if m.matched_html and m.matched_html.text in body_html_texts and m.assignment == "footnote"
    )
    footnote_fn = len(footnote_html) - footnote_tp

    footnote_precision = (
        footnote_tp / (footnote_tp + footnote_fp) if (footnote_tp + footnote_fp) > 0 else 0.0
    )
    footnote_recall = (
        footnote_tp / (footnote_tp + footnote_fn) if (footnote_tp + footnote_fn) > 0 else 0.0
    )
    footnote_f1 = (
        2 * (footnote_precision * footnote_recall) / (footnote_precision + footnote_recall)
        if (footnote_precision + footnote_recall) > 0
        else 0.0
    )

    macro_f1 = (body_f1 + footnote_f1) / 2.0

    return {
        "body_precision": body_precision,
        "body_recall": body_recall,
        "body_f1": body_f1,
        "footnote_precision": footnote_precision,
        "footnote_recall": footnote_recall,
        "footnote_f1": footnote_f1,
        "macro_f1": macro_f1,
        "body_tp": body_tp,
        "body_fp": body_fp,
        "body_fn": body_fn,
        "footnote_tp": footnote_tp,
        "footnote_fp": footnote_fp,
        "footnote_fn": footnote_fn,
    }


def main():
    """Evaluate all PDFs with DP alignment."""
    threshold = 0.3
    gap_penalty = -0.2
    weak_match_penalty = -0.1

    print("=" * 80)
    print("EVALUATING ALL PDFs WITH DP TWO-SEQUENCE ALIGNMENT")
    print("=" * 80)
    print(f"\nThreshold: {threshold}")
    print(f"Gap penalty: {gap_penalty}")
    print(f"Weak match penalty: {weak_match_penalty}")

    # Load PDF names from successful baseline evaluation
    baseline_results = Path("results/sequence_alignment/full_evaluation/all_pdfs_results.csv")
    if not baseline_results.exists():
        print("❌ Baseline results not found! Run baseline evaluation first.")
        return 1

    import csv

    pdf_names = []
    with open(baseline_results) as f:
        reader = csv.DictReader(f)
        pdf_names = [row["pdf_name"] for row in reader]

    print(f"\nFound {len(pdf_names)} PDFs from baseline evaluation")

    results = []
    output_dir = Path("results/sequence_alignment/dp_evaluation")
    output_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 80)
    print("RUNNING DP EVALUATIONS")
    print("=" * 80)

    for idx, pdf_name in enumerate(pdf_names, 1):
        print(f"\n[{idx}/{len(pdf_names)}] 📄 {pdf_name}")
        sys.stdout.flush()

        # Find PDF
        pdf_path = None
        for pdf_dir in [Path("data/v3_data/raw_pdf"), Path("data/raw_pdf")]:
            candidate = pdf_dir / f"{pdf_name}.pdf"
            if candidate.exists():
                pdf_path = candidate
                break

        if not pdf_path:
            print("  ⚠️  PDF not found, skipping")
            continue

        try:
            # Load data
            items = extract_line_level_items(pdf_path)
            body_html, footnote_html = load_html_ground_truth(pdf_name)

            print(
                f"  Lines: {len(items):4d} | Body GT: {len(body_html)} | Footnote GT: {len(footnote_html)}"
            )

            # Run DP alignment
            print("  Running DP alignment...")
            sys.stdout.flush()
            matches = dp_two_sequence_alignment(
                items,
                body_html,
                footnote_html,
                threshold=threshold,
                gap_penalty=gap_penalty,
                weak_match_penalty=weak_match_penalty,
            )

            # Calculate metrics
            metrics = calculate_metrics(matches, body_html, footnote_html)

            print(
                f"  Body F1: {metrics['body_f1']:.3f} | Footnote F1: {metrics['footnote_f1']:.3f} | Macro F1: {metrics['macro_f1']:.3f}"
            )
            sys.stdout.flush()  # Force immediate output

            results.append(
                {
                    "pdf_name": pdf_name,
                    **metrics,
                    "num_lines": len(items),
                    "num_body_gt": len(body_html),
                    "num_footnote_gt": len(footnote_html),
                }
            )

        except Exception as e:
            print(f"  ❌ Error: {e}")
            import traceback

            traceback.print_exc()
            continue

    # Save results
    print("\n" + "=" * 80)
    print("SUMMARY STATISTICS")
    print("=" * 80)

    print(f"\n✅ Successfully evaluated: {len(results)} PDFs")
    print(f"⚠️  Skipped: {len(pdf_names) - len(results)} PDFs")

    if results:
        macro_f1s = [r["macro_f1"] for r in results]
        body_f1s = [r["body_f1"] for r in results]
        footnote_f1s = [r["footnote_f1"] for r in results]

        print("\n📊 Macro F1 Statistics:")
        print(f"  Mean:   {np.mean(macro_f1s):.3f}")
        print(f"  Median: {np.median(macro_f1s):.3f}")
        print(f"  Std:    {np.std(macro_f1s):.3f}")
        print(f"  Min:    {np.min(macro_f1s):.3f}")
        print(f"  Max:    {np.max(macro_f1s):.3f}")

        print("\n📊 Body F1 Statistics:")
        print(f"  Mean:   {np.mean(body_f1s):.3f}")
        print(f"  Median: {np.median(body_f1s):.3f}")
        print(f"  Std:    {np.std(body_f1s):.3f}")
        print(f"  Min:    {np.min(body_f1s):.3f}")
        print(f"  Max:    {np.max(body_f1s):.3f}")

        print("\n📊 Footnote F1 Statistics:")
        print(f"  Mean:   {np.mean(footnote_f1s):.3f}")
        print(f"  Median: {np.median(footnote_f1s):.3f}")
        print(f"  Std:    {np.std(footnote_f1s):.3f}")
        print(f"  Min:    {np.min(footnote_f1s):.3f}")
        print(f"  Max:    {np.max(footnote_f1s):.3f}")

        # Performance distribution
        perfect = sum(1 for f1 in macro_f1s if f1 >= 1.0)
        excellent = sum(1 for f1 in macro_f1s if 0.95 <= f1 < 1.0)
        good = sum(1 for f1 in macro_f1s if 0.80 <= f1 < 0.95)
        fair = sum(1 for f1 in macro_f1s if 0.60 <= f1 < 0.80)
        poor = sum(1 for f1 in macro_f1s if f1 < 0.60)

        print("\n📊 Performance Distribution (Macro F1):")
        print(f"  Perfect (1.00):         {perfect} ({perfect / len(results) * 100:.1f}%)")
        print(f"  Excellent (0.95-1.00):  {excellent} ({excellent / len(results) * 100:.1f}%)")
        print(f"  Good (0.80-0.95):       {good} ({good / len(results) * 100:.1f}%)")
        print(f"  Fair (0.60-0.80):       {fair} ({fair / len(results) * 100:.1f}%)")
        print(f"  Poor (<0.60):           {poor} ({poor / len(results) * 100:.1f}%)")

        # Lowest performers
        sorted_results = sorted(results, key=lambda x: x["macro_f1"])
        print("\n📊 Lowest Performing PDFs (for investigation):")
        for r in sorted_results[:10]:
            name_short = r["pdf_name"][:60]
            print(
                f"  {name_short:60s} | Macro: {r['macro_f1']:.3f} | Body: {r['body_f1']:.3f} | Footnote: {r['footnote_f1']:.3f}"
            )

        # Save CSV
        import csv

        csv_path = output_dir / "all_pdfs_results_dp.csv"
        with open(csv_path, "w", newline="") as f:
            if results:
                writer = csv.DictWriter(f, fieldnames=results[0].keys())
                writer.writeheader()
                writer.writerows(results)
        print(f"\n💾 Saved detailed results to {csv_path}")

        # Save JSON summary
        summary = {
            "threshold": threshold,
            "gap_penalty": gap_penalty,
            "weak_match_penalty": weak_match_penalty,
            "algorithm": "DP two-sequence alignment",
            "num_pdfs": len(results),
            "macro_f1_mean": float(np.mean(macro_f1s)),
            "macro_f1_median": float(np.median(macro_f1s)),
            "macro_f1_std": float(np.std(macro_f1s)),
            "body_f1_mean": float(np.mean(body_f1s)),
            "footnote_f1_mean": float(np.mean(footnote_f1s)),
        }
        json_path = output_dir / "summary_dp.json"
        with open(json_path, "w") as f:
            json.dump(summary, f, indent=2)
        print(f"💾 Saved summary to {json_path}")

    print("\n" + "=" * 80)
    print("DP EVALUATION COMPLETE")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    exit(main())
