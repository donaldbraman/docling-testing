#!/usr/bin/env python3
"""Organize HTML-PDF pairs needing review into a dedicated folder."""

import json
import shutil
from pathlib import Path


def organize_pairs_for_review():
    """Copy problematic pairs to review folder."""
    # Define paths
    html_dir = Path("data/raw_html")
    pdf_dir = Path("data/raw_pdf")
    review_dir = Path("data/pairs_for_review")

    # Create review folder structure
    review_html = review_dir / "html"
    review_pdf = review_dir / "pdf"
    review_html.mkdir(parents=True, exist_ok=True)
    review_pdf.mkdir(parents=True, exist_ok=True)

    # Problematic pairs from validation (partial matches + mismatches)
    # Format: (html_basename, jaccard, overlap, status)
    problematic_pairs = [
        # Partial matches (40-60% Jaccard)
        ("arxiv_2510_14023.html", 42.71, 59.97, "PARTIAL"),
        ("arxiv_2510_14033.html", 42.81, 60.21, "PARTIAL"),
        ("arxiv_2510_14055.html", 40.63, 60.29, "PARTIAL"),
        ("arxiv_2510_14285.html", 33.47, 56.22, "PARTIAL"),
        ("arxiv_2510_14415.html", 46.64, 66.38, "PARTIAL"),
        ("arxiv_2510_14430.html", 42.51, 62.13, "PARTIAL"),
        ("arxiv_2510_14482.html", 36.28, 53.90, "PARTIAL"),
        ("arxiv_2510_14523.html", 47.42, 68.05, "PARTIAL"),
        (
            "indiana_law_journal_foreword.html",
            27.70,
            69.49,
            "PARTIAL",
        ),
        (
            "ucla_law_review_connecting_race_and_empire_what_critical_race_theory_offers_outside_the_us_legal_context.html",
            15.11,
            55.57,
            "PARTIAL",
        ),
        ("usc_law_review_listeners_choices_online.html", 3.09, 67.07, "MISMATCH"),
        # Additional low-score pairs from earlier output
        (
            "wisconsin_law_review_wisconsin_law_review_online_2015_symposium.html",
            20.80,
            47.80,
            "MISMATCH",
        ),
    ]

    # Create summary file
    summary = []

    for html_file, jaccard, overlap, status in problematic_pairs:
        pdf_file = html_file.replace(".html", ".pdf")

        # Copy HTML if exists
        html_path = html_dir / html_file
        if html_path.exists():
            shutil.copy(html_path, review_html / html_file)
            html_copied = True
        else:
            html_copied = False

        # Copy PDF if exists
        pdf_path = pdf_dir / pdf_file
        if pdf_path.exists():
            shutil.copy(pdf_path, review_pdf / pdf_file)
            pdf_copied = True
        else:
            pdf_copied = False

        summary.append(
            {
                "basename": html_file.replace(".html", ""),
                "jaccard": jaccard,
                "overlap": overlap,
                "status": status,
                "html_copied": html_copied,
                "pdf_copied": pdf_copied,
            }
        )

    # Write summary JSON
    summary_file = review_dir / "REVIEW_SUMMARY.json"
    with open(summary_file, "w") as f:
        json.dump(summary, f, indent=2)

    # Write human-readable summary
    readme = review_dir / "README.md"
    with open(readme, "w") as f:
        f.write("# HTML-PDF Pairs for Manual Review\n\n")
        f.write(
            "These pairs scored below 60% Jaccard similarity or showed other quality issues.\n\n"
        )
        f.write("## Review Criteria\n\n")
        f.write("For each pair, verify:\n")
        f.write("1. Are the HTML and PDF about the same article/paper?\n")
        f.write("2. Is the content substantially the same?\n")
        f.write("3. Should we keep this pair for training?\n\n")
        f.write("## Pairs to Review\n\n")
        f.write("| Basename | Jaccard | Overlap | Status |\n")
        f.write("|----------|---------|---------|--------|\n")

        for item in sorted(summary, key=lambda x: x["jaccard"]):
            f.write(
                f"| {item['basename'][:60]}... | {item['jaccard']:.1f}% | {item['overlap']:.1f}% | {item['status']} |\n"
            )

        f.write(f"\n\n**Total pairs to review:** {len(summary)}\n")

    print(f"✅ Organized {len(summary)} pairs for review")
    print(f"📁 Review folder: {review_dir}")
    print(f"📄 Summary: {summary_file}")
    print(f"📄 README: {readme}")

    # Print statistics
    partial = sum(1 for s in summary if s["status"] == "PARTIAL")
    mismatch = sum(1 for s in summary if s["status"] == "MISMATCH")
    print("\n📊 Breakdown:")
    print(f"   - Partial matches (40-60%): {partial}")
    print(f"   - Likely mismatches (<40%): {mismatch}")


if __name__ == "__main__":
    organize_pairs_for_review()
