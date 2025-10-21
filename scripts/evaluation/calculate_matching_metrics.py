#!/usr/bin/env python3
"""
Calculate metrics for fuzzy matching evaluation.

Generates confusion matrices, precision/recall/F1 scores, and comprehensive
evaluation reports for text block matching between extractions and ground truth.
"""

import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from fuzzy_matcher import match_all_items
from parse_extraction import load_extraction
from prepare_matching_data import load_html_ground_truth


@dataclass
class LabelMetrics:
    """Metrics for a single label."""

    label: str
    tp: int  # True positives: correct label on matched text
    fp: int  # False positives: wrong label assigned
    fn: int  # False negatives: ground truth not matched
    precision: float
    recall: float
    f1: float


@dataclass
class EvaluationResult:
    """Complete evaluation result for one PDF."""

    pdf_name: str
    pipeline: str
    total_extraction_items: int
    total_gt_body: int
    total_gt_footnotes: int
    matched: int
    unmatched: int
    match_rate: float
    label_metrics: dict[str, LabelMetrics]
    confusion_matrix: dict[str, dict[str, int]]


def calculate_label_metrics(
    matches: list,
    body_html: list,
    footnote_html: list,
) -> dict[str, LabelMetrics]:
    """
    Calculate precision, recall, F1 for each label type.

    Args:
        matches: List of FuzzyMatch objects
        body_html: Ground truth body text paragraphs
        footnote_html: Ground truth footnote paragraphs

    Returns:
        Dict mapping label name to LabelMetrics
    """
    # Count ground truth items by label
    gt_counts = {"body-text": len(body_html), "footnote-text": len(footnote_html)}

    # Track which ground truth items were matched
    matched_gt = {"body-text": set(), "footnote-text": set()}

    # Count predictions by label
    predicted_counts = defaultdict(int)
    correct_predictions = defaultdict(int)

    for match in matches:
        if match.matched_html is None:
            continue

        predicted_label = match.corrected_label
        predicted_counts[predicted_label] += 1

        # Track which ground truth item was matched (by text content)
        matched_gt[predicted_label].add(match.matched_html.text)

        # Check if prediction is correct (label matches)
        if match.matched_html.label == predicted_label:
            correct_predictions[predicted_label] += 1

    # Calculate metrics per label
    metrics = {}
    for label in ["body-text", "footnote-text"]:
        tp = correct_predictions[label]
        fp = predicted_counts[label] - tp  # Predicted this label but wrong
        fn = gt_counts[label] - len(matched_gt[label])  # GT items not matched

        # Calculate precision, recall, F1
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        metrics[label] = LabelMetrics(
            label=label, tp=tp, fp=fp, fn=fn, precision=precision, recall=recall, f1=f1
        )

    return metrics


def generate_confusion_matrix(matches: list, labels: list[str]) -> dict[str, dict[str, int]]:
    """
    Generate confusion matrix for label predictions.

    Args:
        matches: List of FuzzyMatch objects
        labels: List of label names to include

    Returns:
        Dict mapping true_label -> predicted_label -> count
    """
    matrix = {true_label: dict.fromkeys(labels + ["unmatched"], 0) for true_label in labels}

    for match in matches:
        if match.matched_html is None:
            continue

        true_label = match.matched_html.label
        predicted_label = match.corrected_label if match.corrected_label else "unmatched"

        if true_label in matrix:
            matrix[true_label][predicted_label] += 1

    return matrix


def evaluate_pdf(
    pdf_name: str,
    pipeline: str = "baseline",
    threshold: float = 0.75,
) -> EvaluationResult:
    """
    Evaluate matching performance on a single PDF.

    Args:
        pdf_name: PDF name without extension
        pipeline: Pipeline name (baseline, ocrmypdf, paddleocr)
        threshold: Similarity threshold for matching

    Returns:
        EvaluationResult with complete metrics
    """
    # Load extraction
    ext_file = Path(
        f"results/ocr_pipeline_evaluation/extractions/{pdf_name}_{pipeline}_extraction.json"
    )
    if not ext_file.exists():
        raise FileNotFoundError(f"Extraction not found: {ext_file}")

    items = load_extraction(ext_file)

    # Load ground truth
    body_html, footnote_html = load_html_ground_truth(pdf_name)

    # Match all items
    matches = match_all_items(items, body_html, footnote_html, threshold=threshold)

    # Calculate metrics
    label_metrics = calculate_label_metrics(matches, body_html, footnote_html)

    # Generate confusion matrix
    confusion_matrix = generate_confusion_matrix(matches, ["body-text", "footnote-text"])

    # Count matches
    matched = sum(1 for m in matches if m.matched_html is not None)
    unmatched = len(matches) - matched
    match_rate = matched / len(matches) if matches else 0.0

    return EvaluationResult(
        pdf_name=pdf_name,
        pipeline=pipeline,
        total_extraction_items=len(items),
        total_gt_body=len(body_html),
        total_gt_footnotes=len(footnote_html),
        matched=matched,
        unmatched=unmatched,
        match_rate=match_rate,
        label_metrics=label_metrics,
        confusion_matrix=confusion_matrix,
    )


def save_results_json(results: list[EvaluationResult], output_path: Path):
    """Save evaluation results as JSON."""
    output = []
    for result in results:
        output.append(
            {
                "pdf_name": result.pdf_name,
                "pipeline": result.pipeline,
                "total_extraction_items": result.total_extraction_items,
                "total_gt_body": result.total_gt_body,
                "total_gt_footnotes": result.total_gt_footnotes,
                "matched": result.matched,
                "unmatched": result.unmatched,
                "match_rate": round(result.match_rate, 4),
                "label_metrics": {
                    label: {
                        "tp": m.tp,
                        "fp": m.fp,
                        "fn": m.fn,
                        "precision": round(m.precision, 4),
                        "recall": round(m.recall, 4),
                        "f1": round(m.f1, 4),
                    }
                    for label, m in result.label_metrics.items()
                },
                "confusion_matrix": result.confusion_matrix,
            }
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"✓ Saved JSON results: {output_path}")


def save_results_csv(results: list[EvaluationResult], output_path: Path):
    """Save evaluation results as CSV."""
    import csv

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)

        # Header
        writer.writerow(
            [
                "pdf_name",
                "pipeline",
                "total_items",
                "gt_body",
                "gt_footnotes",
                "matched",
                "unmatched",
                "match_rate",
                "body_precision",
                "body_recall",
                "body_f1",
                "footnote_precision",
                "footnote_recall",
                "footnote_f1",
            ]
        )

        # Data rows
        for result in results:
            body_metrics = result.label_metrics.get("body-text")
            footnote_metrics = result.label_metrics.get("footnote-text")

            writer.writerow(
                [
                    result.pdf_name,
                    result.pipeline,
                    result.total_extraction_items,
                    result.total_gt_body,
                    result.total_gt_footnotes,
                    result.matched,
                    result.unmatched,
                    f"{result.match_rate:.4f}",
                    f"{body_metrics.precision:.4f}" if body_metrics else "0.0000",
                    f"{body_metrics.recall:.4f}" if body_metrics else "0.0000",
                    f"{body_metrics.f1:.4f}" if body_metrics else "0.0000",
                    f"{footnote_metrics.precision:.4f}" if footnote_metrics else "0.0000",
                    f"{footnote_metrics.recall:.4f}" if footnote_metrics else "0.0000",
                    f"{footnote_metrics.f1:.4f}" if footnote_metrics else "0.0000",
                ]
            )

    print(f"✓ Saved CSV results: {output_path}")


def save_confusion_matrix_csv(result: EvaluationResult, output_path: Path):
    """Save confusion matrix as CSV."""
    import csv

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)

        # Header
        labels = ["body-text", "footnote-text"]
        writer.writerow(["True Label \\ Predicted"] + labels + ["unmatched"])

        # Data rows
        for true_label in labels:
            row = [true_label]
            for pred_label in labels + ["unmatched"]:
                count = result.confusion_matrix.get(true_label, {}).get(pred_label, 0)
                row.append(count)
            writer.writerow(row)

    print(f"✓ Saved confusion matrix: {output_path}")


def print_summary(results: list[EvaluationResult]):
    """Print summary of evaluation results."""
    print("\n" + "=" * 80)
    print("EVALUATION SUMMARY")
    print("=" * 80)

    for result in results:
        print(f"\n{result.pdf_name} ({result.pipeline})")
        print(f"  Total items: {result.total_extraction_items}")
        print(
            f"  Ground truth: {result.total_gt_body} body + {result.total_gt_footnotes} footnotes"
        )
        print(
            f"  Matched: {result.matched}/{result.total_extraction_items} ({result.match_rate:.1%})"
        )

        for label, metrics in result.label_metrics.items():
            print(f"\n  {label}:")
            print(f"    Precision: {metrics.precision:.3f}")
            print(f"    Recall:    {metrics.recall:.3f}")
            print(f"    F1:        {metrics.f1:.3f}")
            print(f"    TP/FP/FN:  {metrics.tp}/{metrics.fp}/{metrics.fn}")

    print("\n" + "=" * 80)


def main():
    """Evaluate all PDFs in the test corpus."""
    import argparse

    parser = argparse.ArgumentParser(description="Calculate fuzzy matching metrics")
    parser.add_argument(
        "--pipeline",
        type=str,
        default="baseline",
        choices=["baseline", "ocrmypdf", "paddleocr"],
        help="Pipeline to evaluate (default: baseline)",
    )
    parser.add_argument(
        "--threshold", type=float, default=0.75, help="Similarity threshold (default: 0.75)"
    )
    parser.add_argument(
        "--pdf",
        type=str,
        help="Evaluate specific PDF only (default: all)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results/ocr_pipeline_evaluation/metrics"),
        help="Output directory (default: results/ocr_pipeline_evaluation/metrics)",
    )

    args = parser.parse_args()

    # Get list of PDFs to evaluate
    if args.pdf:
        pdf_names = [args.pdf]
    else:
        # Find all ground truth files
        gt_dir = Path("results/ocr_pipeline_evaluation/ground_truth")
        pdf_names = [
            f.stem.replace("_ground_truth", "") for f in gt_dir.glob("*_ground_truth.json")
        ]

    print(f"Evaluating {len(pdf_names)} PDFs with {args.pipeline} pipeline...")

    # Evaluate each PDF
    results = []
    for pdf_name in sorted(pdf_names):
        print(f"\nProcessing {pdf_name}...")
        try:
            result = evaluate_pdf(pdf_name, args.pipeline, args.threshold)
            results.append(result)

            # Save individual confusion matrix
            cm_path = (
                args.output_dir
                / "confusion_matrices"
                / f"{pdf_name}_{args.pipeline}_confusion_matrix.csv"
            )
            save_confusion_matrix_csv(result, cm_path)

        except FileNotFoundError as e:
            print(f"  ⚠ Skipping: {e}")
            continue

    if not results:
        print("No results to save!")
        return 1

    # Save aggregated results
    json_path = args.output_dir / f"{args.pipeline}_matching_metrics.json"
    csv_path = args.output_dir / f"{args.pipeline}_matching_metrics.csv"

    save_results_json(results, json_path)
    save_results_csv(results, csv_path)

    # Print summary
    print_summary(results)

    return 0


if __name__ == "__main__":
    exit(main())
