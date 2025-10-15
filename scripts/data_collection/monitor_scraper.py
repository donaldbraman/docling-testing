#!/usr/bin/env python3
"""Monitor scraper progress."""

import time
from datetime import datetime
from pathlib import Path


def count_pairs():
    """Count complete HTML-PDF pairs."""
    base_dir = Path(__file__).parent
    html_dir = base_dir / "data" / "raw_html"
    pdf_dir = base_dir / "data" / "raw_pdf"

    html_files = {f.stem for f in html_dir.glob("*.html")}
    pdf_files = {f.stem for f in pdf_dir.glob("*.pdf")}

    return len(html_files & pdf_files)


def main():
    target = 250
    start_time = datetime.now()
    initial_count = count_pairs()

    print(f"Starting monitor at {start_time.strftime('%H:%M:%S')}")
    print(f"Initial pairs: {initial_count}/{target}")
    print("=" * 60)

    while True:
        current = count_pairs()
        elapsed = (datetime.now() - start_time).total_seconds()

        if current > initial_count:
            rate = (current - initial_count) / (elapsed / 60)  # pairs per minute
            remaining = target - current
            eta_minutes = remaining / rate if rate > 0 else 0

            print(
                f"{datetime.now().strftime('%H:%M:%S')} - Progress: {current}/{target} pairs "
                f"(+{current - initial_count}) | Rate: {rate:.1f}/min | ETA: {eta_minutes:.0f} min"
            )
        else:
            print(f"{datetime.now().strftime('%H:%M:%S')} - Progress: {current}/{target} pairs")

        if current >= target:
            print("=" * 60)
            print(f"✓ TARGET REACHED! {current}/{target} pairs collected")
            break

        time.sleep(60)


if __name__ == "__main__":
    main()
