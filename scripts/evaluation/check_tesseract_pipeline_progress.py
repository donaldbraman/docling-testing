#!/usr/bin/env python3
"""
Check progress of the Tesseract corpus pipeline.

Usage:
    uv run python scripts/evaluation/check_tesseract_pipeline_progress.py
"""

import json
from datetime import datetime
from pathlib import Path


def main():
    """Check and display pipeline progress."""
    progress_file = Path("results/tesseract_corpus_pipeline/pipeline_progress.json")
    log_file = Path("corpus_tesseract_pipeline.log")

    print("=" * 80)
    print("TESSERACT CORPUS PIPELINE - PROGRESS CHECK")
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
    print()

    if results:
        print(f"Average time per PDF: {avg_time:.1f}s")
        print(f"Estimated time remaining: {estimated_remaining / 60:.1f} minutes")
        print()

    # Show last 3 processed
    print("Last 3 processed:")
    print("-" * 80)
    for result in results[-3:]:
        status = "✓" if result["success"] else "✗"
        print(f"{status} {result['pdf']:<60} {result['time_s']:.1f}s")

    # Show failures if any
    if failed_count > 0:
        print()
        print("Failed PDFs:")
        print("-" * 80)
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
