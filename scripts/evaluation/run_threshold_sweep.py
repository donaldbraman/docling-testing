#!/usr/bin/env python3
"""
Threshold sweep experiment for sequence alignment algorithms.

Runs all algorithms across different threshold values to find optimal settings.

Usage:
    python scripts/evaluation/run_threshold_sweep.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from fuzzy_matcher import match_all_lines_with_locality
from parse_extraction import ExtractedItem, load_extraction
from prepare_matching_data import load_html_ground_truth
from sequence_alignment.alignment_metrics import calculate_metrics
from sequence_alignment.dp_alignment import dp_two_sequence_alignment
from sequence_alignment.hmm_alignment import hmm_viterbi_alignment
from sequence_alignment.two_pass_alignment import two_pass_alignment


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
                bbox = line["bbox"]  # (x0, y0, x1, y1) in PDF coordinates

                if text.strip():
                    items.append(
                        ExtractedItem(
                            text=text.strip(),
                            label="TEXT",  # Default label
                            page_num=page_num,
                            bbox=bbox,
                            original_docling_label="DocItemLabel.TEXT",
                        )
                    )

    doc.close()
    return items


def run_baseline(items, body_html, footnote_html, threshold):
    """Run baseline locality-aware fuzzy matching."""
    matches = match_all_lines_with_locality(items, body_html, footnote_html, threshold)

    # Convert FuzzyMatch to common format
    class BaselineMatch:
        def __init__(self, fuzzy_match):
            self.extraction_item = fuzzy_match.extraction_item
            self.matched_html = fuzzy_match.matched_html
            self.similarity_score = fuzzy_match.similarity_score
            self.corrected_label = fuzzy_match.corrected_label
            # Determine assignment
            if fuzzy_match.corrected_label == "body-text":
                self.assignment = "body"
            elif fuzzy_match.corrected_label == "footnote-text":
                self.assignment = "footnote"
            else:
                self.assignment = "original"

    return [BaselineMatch(m) for m in matches]


def run_algorithms_at_threshold(items, body_html, footnote_html, threshold):
    """Run all algorithms at a specific threshold."""
    results = {}

    print(f"  Running with threshold={threshold:.2f}...")

    results["baseline"] = run_baseline(items, body_html, footnote_html, threshold)
    results["dp"] = dp_two_sequence_alignment(items, body_html, footnote_html, threshold)
    results["two_pass"] = two_pass_alignment(items, body_html, footnote_html, threshold)
    results["hmm"] = hmm_viterbi_alignment(items, body_html, footnote_html, threshold)

    return results


def main():
    """Run threshold sweep experiment."""
    # Configuration
    thresholds = [0.3, 0.4, 0.5, 0.6, 0.7]
    doc_name = "harvard_law_review_unwarranted_warrants"
    use_line_level = True

    # Paths
    output_dir = Path("results/sequence_alignment/threshold_sweep")
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("THRESHOLD SWEEP EXPERIMENT")
    print("=" * 80)

    # Load data
    if use_line_level:
        print("\n📂 Extracting line-level data from PDF...")
        # Find PDF
        pdf_path = None
        for pdf_dir in [Path("data/v3_data/raw_pdf"), Path("data/raw_pdf")]:
            candidate = pdf_dir / f"{doc_name}.pdf"
            if candidate.exists():
                pdf_path = candidate
                break

        if not pdf_path:
            print(f"Error: PDF not found for {doc_name}")
            return 1

        items = extract_line_level_items(pdf_path)
        print(f"  Extracted {len(items)} lines from PDF")
    else:
        ext_file = Path(
            f"results/ocr_pipeline_evaluation/extractions/{doc_name}_baseline_extraction.json"
        )
        print(f"\n📂 Loading paragraph-level data from {ext_file}...")
        items = load_extraction(ext_file)
        print(f"  Loaded {len(items)} paragraphs")

    body_html, footnote_html = load_html_ground_truth(doc_name)

    print(f"  Body HTML: {len(body_html)} items")
    print(f"  Footnote HTML: {len(footnote_html)} items")
    print(f"  Thresholds to test: {thresholds}")

    # Run experiments across thresholds
    print("\n" + "=" * 80)
    print("RUNNING THRESHOLD SWEEP")
    print("=" * 80)

    all_results = {}
    for threshold in thresholds:
        print(f"\n📊 Threshold {threshold:.2f}:")
        results = run_algorithms_at_threshold(items, body_html, footnote_html, threshold)

        # Calculate metrics
        metrics_dict = {}
        for algo_name, matches in results.items():
            metrics = calculate_metrics(matches, body_html, footnote_html)
            metrics_dict[algo_name] = metrics
            print(
                f"    {algo_name:10s} - Body F1: {metrics.body_f1:.3f}, Footnote F1: {metrics.footnote_f1:.3f}, Macro F1: {metrics.macro_f1:.3f}"
            )

        all_results[threshold] = metrics_dict

    # Create comparison tables
    print("\n" + "=" * 80)
    print("RESULTS SUMMARY")
    print("=" * 80)

    # Table 1: Body F1 scores
    print("\n📊 Body F1 Scores:")
    body_rows = []
    for threshold in thresholds:
        row = {"Threshold": f"{threshold:.1f}"}
        for algo in ["baseline", "dp", "two_pass", "hmm"]:
            row[algo] = f"{all_results[threshold][algo].body_f1:.3f}"
        body_rows.append(row)

    body_df = pd.DataFrame(body_rows)
    print(body_df.to_string(index=False))

    # Table 2: Footnote F1 scores
    print("\n📊 Footnote F1 Scores:")
    footnote_rows = []
    for threshold in thresholds:
        row = {"Threshold": f"{threshold:.1f}"}
        for algo in ["baseline", "dp", "two_pass", "hmm"]:
            row[algo] = f"{all_results[threshold][algo].footnote_f1:.3f}"
        footnote_rows.append(row)

    footnote_df = pd.DataFrame(footnote_rows)
    print(footnote_df.to_string(index=False))

    # Table 3: Macro F1 scores
    print("\n📊 Macro F1 Scores (Average of Body + Footnote):")
    macro_rows = []
    for threshold in thresholds:
        row = {"Threshold": f"{threshold:.1f}"}
        for algo in ["baseline", "dp", "two_pass", "hmm"]:
            row[algo] = f"{all_results[threshold][algo].macro_f1:.3f}"
        macro_rows.append(row)

    macro_df = pd.DataFrame(macro_rows)
    print(macro_df.to_string(index=False))

    # Table 4: Detailed best results per algorithm
    print("\n📊 Best Threshold for Each Algorithm:")
    best_rows = []
    for algo in ["baseline", "dp", "two_pass", "hmm"]:
        best_threshold = None
        best_macro_f1 = 0.0

        for threshold in thresholds:
            macro_f1 = all_results[threshold][algo].macro_f1
            if macro_f1 > best_macro_f1:
                best_macro_f1 = macro_f1
                best_threshold = threshold

        metrics = all_results[best_threshold][algo]
        best_rows.append(
            {
                "Algorithm": algo,
                "Best Threshold": f"{best_threshold:.1f}",
                "Body F1": f"{metrics.body_f1:.3f}",
                "Body Recall": f"{metrics.body_recall:.3f}",
                "Footnote F1": f"{metrics.footnote_f1:.3f}",
                "Footnote Recall": f"{metrics.footnote_recall:.3f}",
                "Macro F1": f"{metrics.macro_f1:.3f}",
            }
        )

    best_df = pd.DataFrame(best_rows)
    print(best_df.to_string(index=False))

    # Save results
    print("\n" + "=" * 80)
    print("SAVING RESULTS")
    print("=" * 80)

    body_df.to_csv(output_dir / "body_f1_by_threshold.csv", index=False)
    footnote_df.to_csv(output_dir / "footnote_f1_by_threshold.csv", index=False)
    macro_df.to_csv(output_dir / "macro_f1_by_threshold.csv", index=False)
    best_df.to_csv(output_dir / "best_thresholds.csv", index=False)

    # Save detailed metrics as JSON
    detailed_results = {}
    for threshold in thresholds:
        detailed_results[f"threshold_{threshold:.1f}"] = {
            algo: metrics.to_dict() for algo, metrics in all_results[threshold].items()
        }

    with open(output_dir / "detailed_results.json", "w") as f:
        json.dump(detailed_results, f, indent=2)

    print(f"  Saved results to {output_dir}/")

    # Final recommendation
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)

    overall_best_algo = None
    overall_best_threshold = None
    overall_best_f1 = 0.0

    for threshold in thresholds:
        for algo, metrics in all_results[threshold].items():
            if metrics.macro_f1 > overall_best_f1:
                overall_best_f1 = metrics.macro_f1
                overall_best_algo = algo
                overall_best_threshold = threshold

    best_metrics = all_results[overall_best_threshold][overall_best_algo]

    print("\n🏆 Overall Best Configuration:")
    print(f"  Algorithm: {overall_best_algo.upper()}")
    print(f"  Threshold: {overall_best_threshold:.1f}")
    print(f"  Macro F1: {best_metrics.macro_f1:.3f}")
    print(
        f"  Body F1: {best_metrics.body_f1:.3f} (Precision: {best_metrics.body_precision:.3f}, Recall: {best_metrics.body_recall:.3f})"
    )
    print(
        f"  Footnote F1: {best_metrics.footnote_f1:.3f} (Precision: {best_metrics.footnote_precision:.3f}, Recall: {best_metrics.footnote_recall:.3f})"
    )

    print("\n" + "=" * 80)
    print("THRESHOLD SWEEP COMPLETE")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    exit(main())
