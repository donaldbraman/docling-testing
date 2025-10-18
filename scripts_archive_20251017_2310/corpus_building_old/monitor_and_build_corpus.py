#!/usr/bin/env python3
"""
Monitor Docling extraction and automatically build corpus when complete.
"""

import subprocess
import time
from datetime import datetime
from pathlib import Path


def count_extracted():
    """Count completed Docling extractions."""
    json_dir = Path("data/raw_pdf")
    return len(list(json_dir.glob("*.docling.json")))


def monitor_extraction(target=179):
    """Monitor extraction progress."""
    print("=" * 80)
    print("MONITORING DOCLING EXTRACTION")
    print("=" * 80)
    print(f"Target: {target} PDFs")
    print(f"Start time: {datetime.now().strftime('%H:%M:%S')}\n")

    last_count = 0
    start_time = time.time()

    while True:
        current = count_extracted()

        if current > last_count:
            elapsed = time.time() - start_time
            rate = current / (elapsed / 60) if elapsed > 0 else 0
            remaining = target - current
            eta_minutes = remaining / rate if rate > 0 else 0

            print(
                f"[{datetime.now().strftime('%H:%M:%S')}] Progress: {current}/{target} "
                f"({current / target * 100:.1f}%) | Rate: {rate:.1f}/min | ETA: {eta_minutes:.0f} min"
            )

            last_count = current

        if current >= target:
            print(f"\n✓ Extraction complete! {current}/{target} PDFs extracted")
            print(f"  Total time: {elapsed / 60:.1f} minutes")
            return True

        time.sleep(30)  # Check every 30 seconds


def main():
    """Monitor extraction and trigger autonomous pipeline."""

    # Monitor until complete
    if monitor_extraction():
        print("\n" + "=" * 80)
        print("STARTING AUTONOMOUS PIPELINE")
        print("=" * 80)

        # Step 1: Build corpus
        print("\n[1/3] Building clean corpus...")
        result = subprocess.run(["uv", "run", "python", "build_clean_corpus.py"])

        if result.returncode != 0:
            print("\n❌ Corpus building failed")
            return

        # Step 2: Train classifier
        print("\n[2/3] Training 7-class classifier...")
        result = subprocess.run(["uv", "run", "python", "train_multiclass_classifier.py"])

        if result.returncode != 0:
            print("\n❌ Training failed")
            return

        # Step 3: Test classifier
        print("\n[3/3] Testing classifier...")
        result = subprocess.run(["uv", "run", "python", "test_multiclass_classifier.py"])

        if result.returncode == 0:
            print("\n" + "=" * 80)
            print("✓ AUTONOMOUS PIPELINE COMPLETE")
            print("=" * 80)
            print("\nReady for PR creation and merge")
        else:
            print("\n❌ Testing failed")


if __name__ == "__main__":
    main()
