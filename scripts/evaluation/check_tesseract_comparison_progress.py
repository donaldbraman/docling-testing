#!/usr/bin/env python3
"""
Check progress of the Tesseract corpus pipeline with comparisons.

Usage:
    uv run python scripts/evaluation/check_tesseract_comparison_progress.py
"""

import json
from datetime import datetime
from pathlib import Path


def main():
    """Check and display pipeline progress with comparison summary."""
    progress_file = Path("results/tesseract_corpus_pipeline/pipeline_progress_with_comparison.json")
    log_file = Path("corpus_tesseract_comparison.log")

    print("=" * 80)
    print("TESSERACT CORPUS PIPELINE WITH COMPARISON - PROGRESS CHECK")
    print("=" * 80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Check if progress file exists
    if not progress_file.exists():
        print("⚠️  Progress file not found. Pipeline may not have started yet.")
        if log_file.exists():
            print("\nLast 10 log lines:")
            print("-" * 80)
            with open(log_file) as f:
                lines = f.readlines()
                for line in lines[-10:]:
                    print(line.rstrip())
        return

    # Load progress
    with open(progress_file) as f:
        data = json.load(f)

    completed = data["completed"]
    total = data["total"]
    results = data["results"]

    # Calculate statistics
    success_count = sum(1 for r in results if r["success"])
    failed_count = sum(1 for r in results if not r["success"])
    compared_count = sum(1 for r in results if r.get("baseline_exists"))

    if results:
        total_time = sum(r["time_s"] for r in results)
        avg_time = total_time / len(results)
        estimated_remaining = avg_time * (total - completed)
    else:
        avg_time = 0
        estimated_remaining = 0

    # Display progress
    progress_pct = (completed / total * 100) if total > 0 else 0
    print(f"Progress: {completed}/{total} PDFs ({progress_pct:.1f}%)")
    print(f"✓ Success: {success_count}")
    print(f"✗ Failed:  {failed_count}")
    print(f"📊 Compared with baseline: {compared_count}")
    print()

    if results:
        print(f"Average time per PDF: {avg_time:.1f}s")
        print(f"Estimated time remaining: {estimated_remaining / 60:.1f} minutes")
        print()

    # Analyze comparisons
    comparisons = [r["comparison"] for r in results if r.get("comparison")]

    if comparisons:
        print("=" * 80)
        print("COMPARISON SUMMARY (Tesseract vs Baseline ocrmac)")
        print("=" * 80)

        # Calculate averages
        avg_coverage = sum(c["coverage_pct"] for c in comparisons) / len(comparisons)
        avg_block_diff = sum(c["block_diff"] for c in comparisons) / len(comparisons)
        avg_char_diff = sum(c["char_diff"] for c in comparisons) / len(comparisons)

        print(f"PDFs compared: {len(comparisons)}")
        print("\nAverage metrics:")
        print(f"  Coverage: {avg_coverage:.1f}% of baseline content")
        print(f"  Block difference: {avg_block_diff:+.1f} blocks")
        print(f"  Character difference: {avg_char_diff:+,.0f} chars")

        # Count improvements
        more_content = sum(1 for c in comparisons if c["coverage_pct"] > 100)
        less_content = sum(1 for c in comparisons if c["coverage_pct"] < 100)

        print("\nContent comparison:")
        print(f"  Tesseract has MORE content: {more_content} PDFs")
        print(f"  Tesseract has LESS content: {less_content} PDFs")

        # Show best/worst cases
        if comparisons:
            best = max(comparisons, key=lambda c: c["coverage_pct"])
            worst = min(comparisons, key=lambda c: c["coverage_pct"])

            print(f"\nBest coverage: {best['coverage_pct']:.1f}%")
            print(f"Worst coverage: {worst['coverage_pct']:.1f}%")

    # Show last 3 processed with comparison details
    print()
    print("=" * 80)
    print("LAST 3 PROCESSED:")
    print("=" * 80)

    for result in results[-3:]:
        status = "✓" if result["success"] else "✗"
        print(f"\n{status} {result['pdf']}")
        print(f"   Time: {result['time_s']:.1f}s")

        if result.get("comparison"):
            comp = result["comparison"]
            print(f"   Blocks: {comp['tesseract_blocks']} vs {comp['baseline_blocks']} (baseline)")
            print(f"   Chars: {comp['tesseract_chars']:,} vs {comp['baseline_chars']:,} (baseline)")
            print(f"   Coverage: {comp['coverage_pct']:.1f}%")

            if comp["coverage_pct"] > 110:
                print(f"   ✓ {comp['coverage_pct'] - 100:.1f}% MORE content than baseline!")
            elif comp["coverage_pct"] < 90:
                print(f"   ⚠️  {100 - comp['coverage_pct']:.1f}% LESS content than baseline")
        elif not result.get("baseline_exists"):
            print("   (No baseline for comparison)")

    # Show failures if any
    if failed_count > 0:
        print()
        print("=" * 80)
        print("FAILED PDFs:")
        print("=" * 80)
        for result in results:
            if not result["success"]:
                print(f"✗ {result['pdf']}")
                print(f"  Error: {result['error']}")

    print()
    print("=" * 80)

    # Show recent log activity
    if log_file.exists():
        print("\nRecent log activity (last 5 lines):")
        print("-" * 80)
        with open(log_file) as f:
            lines = f.readlines()
            for line in lines[-5:]:
                print(line.rstrip())


if __name__ == "__main__":
    main()
