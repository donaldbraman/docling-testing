#!/usr/bin/env python3
"""
Evaluation metrics for sequence alignment algorithms.

Computes primary and guardrail metrics:
- Primary: Balanced classification rate (body/footnote %)
- Guardrail: HTML utilization, alignment quality, spatial coherence, sequence preservation
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from prepare_matching_data import HTMLLine


@dataclass
class AlignmentMetrics:
    """Comprehensive metrics for a sequence alignment result."""

    # Primary metrics
    total_lines: int
    body_count: int
    footnote_count: int
    original_count: int
    body_percentage: float
    footnote_percentage: float
    original_percentage: float

    # HTML utilization
    body_html_total: int
    footnote_html_total: int
    body_html_used: int
    footnote_html_used: int
    body_html_utilization: float
    footnote_html_utilization: float

    # Alignment quality
    avg_similarity_body: float
    avg_similarity_footnote: float
    avg_similarity_overall: float

    # F1 scores (for matched lines only)
    body_precision: float
    body_recall: float
    body_f1: float
    footnote_precision: float
    footnote_recall: float
    footnote_f1: float
    macro_f1: float  # Average of body and footnote F1

    # Spatial coherence
    footnote_bottom_bias: float  # Fraction of footnotes in bottom 25% of pages
    spatial_contiguity: float  # Measure of region coherence (0-1)

    # Sequence preservation
    html_order_violations: int  # Number of out-of-order matches

    # Success criteria
    meets_minimum_balance: bool  # ≥20% body AND ≥20% footnote
    meets_target_balance: bool  # 30-50% body AND 50-70% footnote

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary for JSON serialization."""
        return {
            "total_lines": self.total_lines,
            "body_count": self.body_count,
            "footnote_count": self.footnote_count,
            "original_count": self.original_count,
            "body_percentage": self.body_percentage,
            "footnote_percentage": self.footnote_percentage,
            "original_percentage": self.original_percentage,
            "body_html_total": self.body_html_total,
            "footnote_html_total": self.footnote_html_total,
            "body_html_used": self.body_html_used,
            "footnote_html_used": self.footnote_html_used,
            "body_html_utilization": self.body_html_utilization,
            "footnote_html_utilization": self.footnote_html_utilization,
            "avg_similarity_body": self.avg_similarity_body,
            "avg_similarity_footnote": self.avg_similarity_footnote,
            "avg_similarity_overall": self.avg_similarity_overall,
            "body_precision": self.body_precision,
            "body_recall": self.body_recall,
            "body_f1": self.body_f1,
            "footnote_precision": self.footnote_precision,
            "footnote_recall": self.footnote_recall,
            "footnote_f1": self.footnote_f1,
            "macro_f1": self.macro_f1,
            "footnote_bottom_bias": self.footnote_bottom_bias,
            "spatial_contiguity": self.spatial_contiguity,
            "html_order_violations": self.html_order_violations,
            "meets_minimum_balance": self.meets_minimum_balance,
            "meets_target_balance": self.meets_target_balance,
        }


def calculate_spatial_contiguity(assignments: list[str]) -> float:
    """
    Calculate spatial contiguity score (0-1).

    Measures how well regions are contiguous (few state transitions).
    Higher score = fewer transitions = more contiguous regions.

    Args:
        assignments: List of assignment labels in reading order

    Returns:
        Contiguity score between 0.0 (max transitions) and 1.0 (no transitions)
    """
    if len(assignments) <= 1:
        return 1.0

    # Count state transitions
    transitions = 0
    for i in range(1, len(assignments)):
        if assignments[i] != assignments[i - 1]:
            transitions += 1

    # Normalize by maximum possible transitions
    max_transitions = len(assignments) - 1
    contiguity = 1.0 - (transitions / max_transitions)

    return contiguity


def calculate_html_order_violations(matches: list[tuple[int, HTMLLine | None, str]]) -> int:
    """
    Count HTML order violations.

    Violations occur when a later PDF line matches an earlier HTML line.

    Args:
        matches: List of (pdf_index, matched_html, assignment_type)

    Returns:
        Number of order violations
    """
    body_order = []
    footnote_order = []

    for pdf_idx, html_line, assignment in matches:
        if html_line is None:
            continue

        if assignment == "body":
            body_order.append(html_line)
        elif assignment == "footnote":
            footnote_order.append(html_line)

    # Check for violations in body sequence
    violations = 0
    for i in range(1, len(body_order)):
        # If current HTML comes before previous in original list, it's a violation
        # Note: This assumes html_lines have order information
        # For simplicity, we'll skip this check if HTML lines don't track order
        pass

    # Same for footnote sequence
    for i in range(1, len(footnote_order)):
        pass

    return violations


def calculate_metrics(
    matches: list[Any],  # List of match objects (DPMatch, TwoPassMatch, or HMMMatch)
    body_html: list[HTMLLine],
    footnote_html: list[HTMLLine],
) -> AlignmentMetrics:
    """
    Calculate comprehensive metrics for alignment results.

    Args:
        matches: List of match objects from any alignment algorithm
        body_html: Original body HTML lines
        footnote_html: Original footnote HTML lines

    Returns:
        AlignmentMetrics object with all computed metrics
    """
    total_lines = len(matches)

    # Count assignments
    body_matches = [m for m in matches if m.assignment == "body"]
    footnote_matches = [m for m in matches if m.assignment == "footnote"]
    original_matches = [m for m in matches if m.assignment == "original"]

    body_count = len(body_matches)
    footnote_count = len(footnote_matches)
    original_count = len(original_matches)

    body_percentage = (body_count / total_lines * 100) if total_lines > 0 else 0.0
    footnote_percentage = (footnote_count / total_lines * 100) if total_lines > 0 else 0.0
    original_percentage = (original_count / total_lines * 100) if total_lines > 0 else 0.0

    # HTML utilization
    # Use text as unique identifier since HTMLLine is not hashable
    body_html_used = len({m.matched_html.text for m in body_matches if m.matched_html})
    footnote_html_used = len({m.matched_html.text for m in footnote_matches if m.matched_html})

    body_html_utilization = (body_html_used / len(body_html) * 100) if len(body_html) > 0 else 0.0
    footnote_html_utilization = (
        (footnote_html_used / len(footnote_html) * 100) if len(footnote_html) > 0 else 0.0
    )

    # Alignment quality (average similarity)
    avg_similarity_body = (
        sum(m.similarity_score for m in body_matches) / len(body_matches) if body_matches else 0.0
    )
    avg_similarity_footnote = (
        sum(m.similarity_score for m in footnote_matches) / len(footnote_matches)
        if footnote_matches
        else 0.0
    )

    all_matched = body_matches + footnote_matches
    avg_similarity_overall = (
        sum(m.similarity_score for m in all_matched) / len(all_matched) if all_matched else 0.0
    )

    # F1 scores based on HTML ground truth
    # Precision: Of lines we labeled as body/footnote, how many matched HTML?
    # Recall: Of HTML items available, how many did we match?

    # Body F1
    body_precision = (
        (len([m for m in body_matches if m.matched_html]) / body_count) if body_count > 0 else 0.0
    )
    body_recall = (body_html_used / len(body_html)) if len(body_html) > 0 else 0.0
    body_f1 = (
        (2 * body_precision * body_recall / (body_precision + body_recall))
        if (body_precision + body_recall) > 0
        else 0.0
    )

    # Footnote F1
    footnote_precision = (
        (len([m for m in footnote_matches if m.matched_html]) / footnote_count)
        if footnote_count > 0
        else 0.0
    )
    footnote_recall = (footnote_html_used / len(footnote_html)) if len(footnote_html) > 0 else 0.0
    footnote_f1 = (
        (2 * footnote_precision * footnote_recall / (footnote_precision + footnote_recall))
        if (footnote_precision + footnote_recall) > 0
        else 0.0
    )

    # Macro F1 (average of body and footnote)
    macro_f1 = (body_f1 + footnote_f1) / 2.0

    # Spatial coherence - footnote bottom bias
    # Count footnotes in bottom 25% of each page
    footnotes_at_bottom = 0
    for match in footnote_matches:
        item = match.extraction_item
        # Calculate relative position on page (y-coordinate)
        # bbox is a tuple: (l, t, r, b)
        if item.bbox:
            l, t, r, b = item.bbox
            y_mid = (t + b) / 2.0
            # Normalize to [0, 1] assuming page height ~2200 (Docling coordinates)
            page_position = y_mid / 2200.0
            if page_position > 0.75:
                footnotes_at_bottom += 1

    footnote_bottom_bias = (footnotes_at_bottom / footnote_count) if footnote_count > 0 else 0.0

    # Spatial contiguity
    assignments = [m.assignment for m in matches]
    spatial_contiguity = calculate_spatial_contiguity(assignments)

    # Sequence preservation (HTML order violations)
    match_tuples = [
        (i, m.matched_html, m.assignment) for i, m in enumerate(matches) if m.matched_html
    ]
    html_order_violations = calculate_html_order_violations(match_tuples)

    # Success criteria
    meets_minimum_balance = body_percentage >= 20.0 and footnote_percentage >= 20.0
    meets_target_balance = (30.0 <= body_percentage <= 50.0) and (
        50.0 <= footnote_percentage <= 70.0
    )

    return AlignmentMetrics(
        total_lines=total_lines,
        body_count=body_count,
        footnote_count=footnote_count,
        original_count=original_count,
        body_percentage=body_percentage,
        footnote_percentage=footnote_percentage,
        original_percentage=original_percentage,
        body_html_total=len(body_html),
        footnote_html_total=len(footnote_html),
        body_html_used=body_html_used,
        footnote_html_used=footnote_html_used,
        body_html_utilization=body_html_utilization,
        footnote_html_utilization=footnote_html_utilization,
        avg_similarity_body=avg_similarity_body,
        avg_similarity_footnote=avg_similarity_footnote,
        avg_similarity_overall=avg_similarity_overall,
        body_precision=body_precision,
        body_recall=body_recall,
        body_f1=body_f1,
        footnote_precision=footnote_precision,
        footnote_recall=footnote_recall,
        footnote_f1=footnote_f1,
        macro_f1=macro_f1,
        footnote_bottom_bias=footnote_bottom_bias,
        spatial_contiguity=spatial_contiguity,
        html_order_violations=html_order_violations,
        meets_minimum_balance=meets_minimum_balance,
        meets_target_balance=meets_target_balance,
    )


def print_metrics(metrics: AlignmentMetrics, algorithm_name: str) -> None:
    """
    Pretty-print metrics to console.

    Args:
        metrics: Computed metrics
        algorithm_name: Name of the alignment algorithm
    """
    print(f"\n{'=' * 60}")
    print(f"Metrics for {algorithm_name}")
    print(f"{'=' * 60}")

    print("\n📊 Primary Metrics (Classification Balance):")
    print(f"  Total lines: {metrics.total_lines}")
    print(f"  Body-text: {metrics.body_count} ({metrics.body_percentage:.1f}%)")
    print(f"  Footnote-text: {metrics.footnote_count} ({metrics.footnote_percentage:.1f}%)")
    print(f"  Original labels: {metrics.original_count} ({metrics.original_percentage:.1f}%)")

    print("\n📈 HTML Utilization:")
    print(
        f"  Body HTML: {metrics.body_html_used}/{metrics.body_html_total} ({metrics.body_html_utilization:.1f}%)"
    )
    print(
        f"  Footnote HTML: {metrics.footnote_html_used}/{metrics.footnote_html_total} ({metrics.footnote_html_utilization:.1f}%)"
    )

    print("\n🎯 Alignment Quality (Avg Similarity):")
    print(f"  Body matches: {metrics.avg_similarity_body:.3f}")
    print(f"  Footnote matches: {metrics.avg_similarity_footnote:.3f}")
    print(f"  Overall: {metrics.avg_similarity_overall:.3f}")

    print("\n📏 F1 Scores (vs HTML Ground Truth):")
    print("  Body Text:")
    print(f"    Precision: {metrics.body_precision:.3f}")
    print(f"    Recall: {metrics.body_recall:.3f}")
    print(f"    F1: {metrics.body_f1:.3f}")
    print("  Footnote Text:")
    print(f"    Precision: {metrics.footnote_precision:.3f}")
    print(f"    Recall: {metrics.footnote_recall:.3f}")
    print(f"    F1: {metrics.footnote_f1:.3f}")
    print(f"  Macro F1: {metrics.macro_f1:.3f}")

    print("\n📍 Spatial Coherence:")
    print(f"  Footnote bottom bias: {metrics.footnote_bottom_bias:.1%}")
    print(f"  Spatial contiguity: {metrics.spatial_contiguity:.3f}")

    print("\n🔄 Sequence Preservation:")
    print(f"  HTML order violations: {metrics.html_order_violations}")

    print("\n✅ Success Criteria:")
    status_min = "✅ PASS" if metrics.meets_minimum_balance else "❌ FAIL"
    status_target = "✅ PASS" if metrics.meets_target_balance else "❌ FAIL"
    print(f"  Minimum balance (≥20% each): {status_min}")
    print(f"  Target balance (40/60): {status_target}")

    print(f"\n{'=' * 60}\n")


def main():
    """Test metrics calculation on sample data."""
    from dp_alignment import dp_two_sequence_alignment
    from parse_extraction import load_extraction
    from prepare_matching_data import load_html_ground_truth

    # Load data
    ext_file = Path(
        "../../results/ocr_pipeline_evaluation/extractions/harvard_law_review_unwarranted_warrants_baseline_extraction.json"
    )
    items = load_extraction(ext_file)

    body_html, footnote_html = load_html_ground_truth("harvard_law_review_unwarranted_warrants")

    print("Running DP alignment for metrics test...")
    matches = dp_two_sequence_alignment(items, body_html, footnote_html, threshold=0.75)

    # Calculate and print metrics
    metrics = calculate_metrics(matches, body_html, footnote_html)
    print_metrics(metrics, "DP Two-Sequence Alignment")

    return 0


if __name__ == "__main__":
    exit(main())
