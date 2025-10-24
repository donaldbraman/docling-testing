#!/usr/bin/env python3
"""
Analyze body:footnote text ratios in HTML ground truth documents.
"""

import json
from pathlib import Path


def create_histogram(values: list[float], labels: list[str], title: str, num_bins: int = 10) -> str:
    """Create a simple ASCII histogram with document labels."""
    if not values:
        return "No data"

    # Define bins
    min_val = min(values)
    max_val = max(values)

    # Use logarithmic bins for ratios
    import math

    if min_val > 0:
        log_min = math.log10(min_val)
        log_max = math.log10(max_val)
        bin_edges = [
            10 ** (log_min + i * (log_max - log_min) / num_bins) for i in range(num_bins + 1)
        ]
    else:
        # Linear bins if we have zeros
        bin_width = (max_val - min_val) / num_bins if max_val > min_val else 1.0
        bin_edges = [min_val + i * bin_width for i in range(num_bins + 1)]

    # Assign values to bins
    bins = [[] for _ in range(num_bins)]
    for value, label in zip(values, labels, strict=False):
        for i in range(num_bins):
            if bin_edges[i] <= value < bin_edges[i + 1] or (
                i == num_bins - 1 and value == bin_edges[i + 1]
            ):
                bins[i].append(label)
                break

    # Find max count for scaling
    max_count = max(len(b) for b in bins)

    # Build histogram
    lines = [f"\n{title}"]
    lines.append("=" * 80)

    for i, docs in enumerate(bins):
        count = len(docs)
        bar_length = int(40 * count / max_count) if max_count > 0 else 0
        bar = "█" * bar_length

        # Format ratio range
        if min_val > 0 and max_val / min_val > 100:  # Use log scale
            label = f"{bin_edges[i]:6.2f} - {bin_edges[i + 1]:6.2f}"
        else:
            label = f"{bin_edges[i]:6.2f} - {bin_edges[i + 1]:6.2f}"

        lines.append(f"{label} | {bar} {count:2d}")
        if docs:
            for doc in docs:
                lines.append(f"           └─ {doc}")

    return "\n".join(lines)


def main():
    gt_dir = Path("results/ocr_pipeline_evaluation/ground_truth")
    gt_files = sorted(gt_dir.glob("*_ground_truth.json"))

    print(f"Analyzing {len(gt_files)} ground truth documents...\n")

    results = []
    for gt_path in gt_files:
        with open(gt_path) as f:
            data = json.load(f)

        doc_name = gt_path.stem.replace("_ground_truth", "")

        body_text = " ".join([p["text"] for p in data["body_text_paragraphs"]])
        footnote_text = " ".join([p["text"] for p in data.get("footnotes", [])])

        body_chars = len(body_text)
        footnote_chars = len(footnote_text)
        total_chars = body_chars + footnote_chars

        body_fn_ratio = (
            body_chars / footnote_chars if footnote_chars > 0 else float("inf")
        )  # No footnotes if inf

        fn_body_ratio = (
            footnote_chars / body_chars if body_chars > 0 else float("inf")
        )  # No body (shouldn't happen) if inf

        body_pct = 100 * body_chars / total_chars if total_chars > 0 else 0
        footnote_pct = 100 * footnote_chars / total_chars if total_chars > 0 else 0

        results.append(
            {
                "doc_name": doc_name,
                "body_chars": body_chars,
                "footnote_chars": footnote_chars,
                "total_chars": total_chars,
                "body_pct": body_pct,
                "footnote_pct": footnote_pct,
                "body_fn_ratio": body_fn_ratio,
                "fn_body_ratio": fn_body_ratio,
            }
        )

    # Print table
    print("=" * 120)
    print("HTML GROUND TRUTH: BODY vs FOOTNOTE TEXT DISTRIBUTION")
    print("=" * 120)
    print(
        f"{'Document':<60} {'Body':<15} {'Footnotes':<15} {'Body %':<10} {'Footnote %':<10} {'Body:FN':<10}"
    )
    print("-" * 120)

    for r in sorted(results, key=lambda x: x["body_fn_ratio"]):
        ratio_str = (
            f"{r['body_fn_ratio']:.2f}" if r["body_fn_ratio"] != float("inf") else "∞ (no FN)"
        )
        print(
            f"{r['doc_name']:<60} {r['body_chars']:>12,}  {r['footnote_chars']:>12,}  {r['body_pct']:>8.1f}%  {r['footnote_pct']:>8.1f}%  {ratio_str:>10}"
        )

    # Summary statistics
    finite_ratios = [r["body_fn_ratio"] for r in results if r["body_fn_ratio"] != float("inf")]
    body_pcts = [r["body_pct"] for r in results]
    footnote_pcts = [r["footnote_pct"] for r in results]

    print("\n" + "=" * 120)
    print("SUMMARY STATISTICS")
    print("=" * 120)
    print(f"Mean body percentage: {sum(body_pcts) / len(body_pcts):.1f}%")
    print(f"Mean footnote percentage: {sum(footnote_pcts) / len(footnote_pcts):.1f}%")
    print("\nBody:Footnote ratio (excluding docs with no footnotes):")
    print(f"  Mean: {sum(finite_ratios) / len(finite_ratios):.2f}")
    print(f"  Min:  {min(finite_ratios):.2f}")
    print(f"  Max:  {max(finite_ratios):.2f}")

    # Create histogram for body percentage
    labels = [r["doc_name"][:40] for r in results]
    body_pcts_sorted = [r["body_pct"] for r in results]
    print(create_histogram(body_pcts_sorted, labels, "BODY TEXT PERCENTAGE DISTRIBUTION"))

    # Create histogram for footnote percentage
    print(create_histogram(footnote_pcts, labels, "FOOTNOTE TEXT PERCENTAGE DISTRIBUTION"))

    # Create histogram for body:footnote ratio (finite only)
    finite_labels = [r["doc_name"][:40] for r in results if r["body_fn_ratio"] != float("inf")]
    print(create_histogram(finite_ratios, finite_labels, "BODY:FOOTNOTE RATIO DISTRIBUTION"))


if __name__ == "__main__":
    main()
