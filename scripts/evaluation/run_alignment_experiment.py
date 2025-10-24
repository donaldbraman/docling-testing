#!/usr/bin/env python3
"""
Experimental harness for sequence alignment algorithms.

Runs all three alignment approaches + baseline and generates comparison metrics.

Usage:
    python scripts/evaluation/run_alignment_experiment.py

Output:
    - results/sequence_alignment/metrics/*.json (individual metrics)
    - results/sequence_alignment/metrics/comparison_table.csv (summary comparison)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from fuzzy_matcher import match_all_lines_with_locality
from parse_extraction import load_extraction
from prepare_matching_data import load_html_ground_truth
from sequence_alignment.alignment_metrics import calculate_metrics, print_metrics
from sequence_alignment.dp_alignment import dp_two_sequence_alignment
from sequence_alignment.hmm_alignment import hmm_viterbi_alignment
from sequence_alignment.two_pass_alignment import two_pass_alignment


def run_baseline(items, body_html, footnote_html, threshold=0.75):
    """Run baseline locality-aware fuzzy matching."""
    print("\n🔄 Running baseline (locality-aware fuzzy matching)...")
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


def run_all_algorithms(items, body_html, footnote_html, threshold=0.75) -> dict[str, list]:
    """
    Run all alignment algorithms.

    Returns:
        Dictionary mapping algorithm name to list of match results
    """
    results = {}

    # Baseline
    results["baseline"] = run_baseline(items, body_html, footnote_html, threshold)

    # DP
    print("\n🔄 Running DP two-sequence alignment...")
    results["dp"] = dp_two_sequence_alignment(items, body_html, footnote_html, threshold)

    # Two-Pass
    print("\n🔄 Running Two-Pass Needleman-Wunsch...")
    results["two_pass"] = two_pass_alignment(items, body_html, footnote_html, threshold)

    # HMM
    print("\n🔄 Running HMM Viterbi...")
    results["hmm"] = hmm_viterbi_alignment(items, body_html, footnote_html, threshold)

    return results


def save_metrics(metrics_dict: dict, output_dir: Path) -> None:
    """
    Save individual metrics to JSON files.

    Args:
        metrics_dict: Dictionary mapping algorithm name to AlignmentMetrics
        output_dir: Output directory for metrics files
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    for algo_name, metrics in metrics_dict.items():
        output_file = output_dir / f"{algo_name}_metrics.json"
        with open(output_file, "w") as f:
            json.dump(metrics.to_dict(), f, indent=2)
        print(f"  Saved {algo_name} metrics to {output_file}")


def create_comparison_table(metrics_dict: dict, output_dir: Path) -> pd.DataFrame:
    """
    Create comparison table across all algorithms.

    Args:
        metrics_dict: Dictionary mapping algorithm name to AlignmentMetrics
        output_dir: Output directory for comparison table

    Returns:
        Pandas DataFrame with comparison
    """
    rows = []

    for algo_name, metrics in metrics_dict.items():
        rows.append(
            {
                "Algorithm": algo_name,
                "Body F1": f"{metrics.body_f1:.3f}",
                "Body Prec": f"{metrics.body_precision:.3f}",
                "Body Rec": f"{metrics.body_recall:.3f}",
                "Footnote F1": f"{metrics.footnote_f1:.3f}",
                "Footnote Prec": f"{metrics.footnote_precision:.3f}",
                "Footnote Rec": f"{metrics.footnote_recall:.3f}",
                "Macro F1": f"{metrics.macro_f1:.3f}",
                "Body HTML": f"{metrics.body_html_used}/{metrics.body_html_total}",
                "Footnote HTML": f"{metrics.footnote_html_used}/{metrics.footnote_html_total}",
            }
        )

    df = pd.DataFrame(rows)

    # Save to CSV
    output_file = output_dir / "comparison_table.csv"
    df.to_csv(output_file, index=False)
    print(f"\n📊 Saved comparison table to {output_file}")

    return df


def extract_line_level_items(pdf_path: Path) -> list:
    """Extract line-level text from PDF as ExtractedItem objects."""
    import fitz
    from parse_extraction import ExtractedItem

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


def main():
    """Run alignment experiment and generate comparison."""
    # Configuration
    threshold = 0.75
    doc_name = "harvard_law_review_unwarranted_warrants"
    use_line_level = True  # Use line-level extraction instead of paragraph-level

    # Paths
    output_dir = Path("results/sequence_alignment/metrics")

    print("=" * 80)
    print("SEQUENCE ALIGNMENT EXPERIMENT")
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
    print(f"  Threshold: {threshold}")

    # Run all algorithms
    print("\n" + "=" * 80)
    print("RUNNING ALGORITHMS")
    print("=" * 80)

    results = run_all_algorithms(items, body_html, footnote_html, threshold)

    # Calculate metrics for each
    print("\n" + "=" * 80)
    print("CALCULATING METRICS")
    print("=" * 80)

    metrics_dict = {}
    for algo_name, matches in results.items():
        print(f"\n📊 Calculating metrics for {algo_name}...")
        metrics = calculate_metrics(matches, body_html, footnote_html)
        metrics_dict[algo_name] = metrics

    # Print all metrics
    print("\n" + "=" * 80)
    print("DETAILED METRICS")
    print("=" * 80)

    for algo_name, metrics in metrics_dict.items():
        print_metrics(metrics, algo_name.upper())

    # Save metrics to JSON
    print("\n" + "=" * 80)
    print("SAVING RESULTS")
    print("=" * 80)

    save_metrics(metrics_dict, output_dir)

    # Create and display comparison table
    print("\n" + "=" * 80)
    print("COMPARISON TABLE")
    print("=" * 80)

    df = create_comparison_table(metrics_dict, output_dir)
    print("\n" + df.to_string(index=False))

    # Summary recommendation
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)

    # Find best algorithm based on body F1
    best_algo = None
    best_f1 = 0.0

    for algo_name, metrics in metrics_dict.items():
        if metrics.body_f1 > best_f1:
            best_f1 = metrics.body_f1
            best_algo = algo_name

    print(f"\n🏆 Best algorithm (by Body F1): {best_algo.upper()}")
    print(f"  Body F1: {metrics_dict[best_algo].body_f1:.3f}")
    print(f"  Body Precision: {metrics_dict[best_algo].body_precision:.3f}")
    print(f"  Body Recall: {metrics_dict[best_algo].body_recall:.3f}")
    print(
        f"  Body HTML Used: {metrics_dict[best_algo].body_html_used}/{metrics_dict[best_algo].body_html_total}"
    )
    print(
        f"  Body Lines: {metrics_dict[best_algo].body_count} ({metrics_dict[best_algo].body_percentage:.1f}%)"
    )

    print("\n" + "=" * 80)
    print("EXPERIMENT COMPLETE")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    exit(main())
