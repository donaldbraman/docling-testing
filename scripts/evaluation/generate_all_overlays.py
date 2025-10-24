#!/usr/bin/env python3
"""
Generate color overlay PDFs for all documents with ground truth.

Creates visual overlays showing body text (green) and footnotes (blue) classification.

Usage:
    python scripts/evaluation/generate_all_overlays.py [--threshold THRESHOLD]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from generate_overlay_pdfs import create_corrected_overlay_pdf
from prepare_matching_data import load_html_ground_truth


def main():
    """Generate overlay PDFs for all documents."""
    parser = argparse.ArgumentParser(description="Generate overlay PDFs for all documents")
    parser.add_argument(
        "--threshold", type=float, default=0.3, help="Similarity threshold (default: 0.3)"
    )
    parser.add_argument(
        "--algorithm",
        type=str,
        default="baseline",
        choices=["baseline", "dp", "two_pass", "hmm"],
        help="Algorithm to use (default: baseline)",
    )
    args = parser.parse_args()

    print("=" * 80)
    print("GENERATING COLOR OVERLAY PDFs")
    print("=" * 80)
    print(f"\nThreshold: {args.threshold}")
    print(f"Algorithm: {args.algorithm}")

    # Find all ground truth files
    gt_dir = Path("data/v3_data/processed_html")
    gt_files = sorted(gt_dir.glob("*.json"))

    print(f"\nFound {len(gt_files)} PDFs with ground truth")

    # Output directory
    output_dir = Path("results/sequence_alignment/overlay_pdfs")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Find corresponding PDFs
    pdf_dirs = [Path("data/v3_data/raw_pdf"), Path("data/raw_pdf")]

    print("\n" + "=" * 80)
    print("GENERATING OVERLAYS")
    print("=" * 80)

    success_count = 0
    skip_count = 0

    for i, gt_file in enumerate(gt_files, 1):
        pdf_name = gt_file.stem

        # Find PDF file
        pdf_path = None
        for pdf_dir in pdf_dirs:
            candidate = pdf_dir / f"{pdf_name}.pdf"
            if candidate.exists():
                pdf_path = candidate
                break

        if not pdf_path:
            print(f"\n[{i}/{len(gt_files)}] ⚠️  {pdf_name}")
            print("  PDF not found, skipping")
            skip_count += 1
            continue

        try:
            print(f"\n[{i}/{len(gt_files)}] 📄 {pdf_name}")

            # Load ground truth
            body_html, footnote_html = load_html_ground_truth(pdf_name)

            # Create output path
            output_path = output_dir / f"{pdf_name}_overlay.pdf"

            # Generate overlay
            create_corrected_overlay_pdf(
                pdf_path=pdf_path,
                body_html=body_html,
                footnote_html=footnote_html,
                output_path=output_path,
                threshold=args.threshold,
                algorithm=args.algorithm,
            )

            print(f"  ✅ Created: {output_path}")
            success_count += 1
            sys.stdout.flush()

        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
            skip_count += 1
            continue

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    print(f"\n✅ Successfully generated: {success_count} overlay PDFs")
    print(f"⚠️  Skipped: {skip_count} PDFs")
    print(f"\n📂 Output directory: {output_dir}")
    print(
        f"   Total size: {sum(f.stat().st_size for f in output_dir.glob('*.pdf')) / 1024 / 1024:.1f} MB"
    )

    print("\n" + "=" * 80)
    print("OVERLAY GENERATION COMPLETE")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    exit(main())
