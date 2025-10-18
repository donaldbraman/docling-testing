#!/usr/bin/env python3
"""Create folder with high-quality law review pairs only (>60% Jaccard, no arXiv)."""

import csv
import shutil
from pathlib import Path


def create_high_quality_law_review_folder():
    """Copy law review pairs with >60% Jaccard to review folder."""
    # Source: paired corpus review folder (has all current pairs)
    source_dir = Path("data/paired_corpus_review")
    review_dir = Path("data/high_quality_law_reviews")

    # Create review directory
    review_dir.mkdir(parents=True, exist_ok=True)

    print("📋 Creating high-quality law review review folder...\n")

    # Load quality scores
    scores = {}
    with open("data/law_review_quality_scores.csv") as f:
        reader = csv.DictReader(f)
        for row in reader:
            scores[row["Basename"]] = float(row["Jaccard_Similarity"])

    # Filter law review pairs with >60% Jaccard
    high_quality = []
    for basename, jaccard in scores.items():
        if jaccard > 60 and not basename.startswith("arxiv_"):
            html_file = source_dir / f"{basename}.html"
            pdf_file = source_dir / f"{basename}.pdf"

            # Only include if both files exist
            if html_file.exists() and pdf_file.exists():
                high_quality.append((basename, jaccard))

    high_quality.sort(key=lambda x: x[1], reverse=True)

    print(f"Found {len(high_quality)} law review pairs with >60% Jaccard\n")

    # Copy files
    for basename, jaccard in high_quality:
        html_file = source_dir / f"{basename}.html"
        pdf_file = source_dir / f"{basename}.pdf"

        shutil.copy(html_file, review_dir / html_file.name)
        shutil.copy(pdf_file, review_dir / pdf_file.name)

    print(f"✅ Copied {len(high_quality)} HTML files")
    print(f"✅ Copied {len(high_quality)} PDF files")
    print(f"\n📁 Review folder: {review_dir.absolute()}")
    print(f"\n📊 Total files: {len(high_quality) * 2}")

    # Score statistics
    if high_quality:
        scores_list = [jaccard for _, jaccard in high_quality]
        print("\nQuality score range:")
        print(f"   Min: {min(scores_list):.1f}%")
        print(f"   Max: {max(scores_list):.1f}%")
        print(f"   Avg: {sum(scores_list) / len(scores_list):.1f}%")
    else:
        print("\n⚠️  No high-quality pairs found!")
        return

    # Create README
    readme = review_dir / "README.md"
    with open(readme, "w") as f:
        f.write("# High-Quality Law Review Pairs\n\n")
        f.write("This folder contains only law review pairs with >60% Jaccard similarity.\n\n")
        f.write("## Contents\n\n")
        f.write(f"- **Total pairs:** {len(high_quality)}\n")
        f.write(f"- **Total files:** {len(high_quality) * 2}\n")
        f.write("- **Quality threshold:** >60% Jaccard similarity\n\n")
        f.write("## Quality Distribution\n\n")
        excellent = sum(1 for _, j in high_quality if j >= 80)
        good = sum(1 for _, j in high_quality if 60 < j < 80)
        f.write(f"- **Excellent (≥80%):** {excellent} pairs\n")
        f.write(f"- **Good (60-80%):** {good} pairs\n\n")
        f.write("## Score Statistics\n\n")
        f.write(f"- **Minimum:** {min(scores_list):.1f}%\n")
        f.write(f"- **Maximum:** {max(scores_list):.1f}%\n")
        f.write(f"- **Average:** {sum(scores_list) / len(scores_list):.1f}%\n\n")
        f.write("## Pairs List\n\n")
        f.write("| Score | Basename |\n")
        f.write("|-------|----------|\n")
        for basename, jaccard in high_quality:
            f.write(f"| {jaccard:.1f}% | {basename} |\n")

    print(f"\n📄 README created: {readme}")
    print(
        f"\n✅ Review folder ready! All {len(high_quality)} high-quality law review pairs in one location."
    )


if __name__ == "__main__":
    create_high_quality_law_review_folder()
