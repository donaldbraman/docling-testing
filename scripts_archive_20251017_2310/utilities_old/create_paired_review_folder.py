#!/usr/bin/env python3
"""Create a single folder with all paired HTML-PDF files for easy review."""

import shutil
from pathlib import Path


def create_paired_review_folder():
    """Copy all paired HTML and PDF files to a single review folder."""
    html_dir = Path("data/raw_html")
    pdf_dir = Path("data/raw_pdf")
    review_dir = Path("data/paired_corpus_review")

    # Create review directory
    review_dir.mkdir(parents=True, exist_ok=True)

    print("📋 Creating paired corpus review folder...\n")

    # Copy all HTML files
    html_files = list(html_dir.glob("*.html"))
    for html_file in html_files:
        shutil.copy(html_file, review_dir / html_file.name)

    # Copy all PDF files
    pdf_files = list(pdf_dir.glob("*.pdf"))
    for pdf_file in pdf_files:
        shutil.copy(pdf_file, review_dir / pdf_file.name)

    print(f"✅ Copied {len(html_files)} HTML files")
    print(f"✅ Copied {len(pdf_files)} PDF files")
    print(f"\n📁 Review folder: {review_dir.absolute()}")
    print(f"\n📊 Total files: {len(html_files) + len(pdf_files)}")

    # Breakdown
    arxiv_html = len([f for f in html_files if f.stem.startswith("arxiv_")])
    arxiv_pdf = len([f for f in pdf_files if f.stem.startswith("arxiv_")])
    law_html = len(html_files) - arxiv_html
    law_pdf = len(pdf_files) - arxiv_pdf

    print(f"\n   arXiv: {arxiv_html} HTML + {arxiv_pdf} PDF")
    print(f"   Law reviews: {law_html} HTML + {law_pdf} PDF")

    # Create README
    readme = review_dir / "README.md"
    with open(readme, "w") as f:
        f.write("# Paired Corpus Review\n\n")
        f.write("This folder contains all paired HTML-PDF files for the training corpus.\n\n")
        f.write("## Contents\n\n")
        f.write(f"- **Total files:** {len(html_files) + len(pdf_files)}\n")
        f.write(f"- **HTML files:** {len(html_files)}\n")
        f.write(f"- **PDF files:** {len(pdf_files)}\n")
        f.write(f"- **Matched pairs:** {len(html_files)}\n\n")
        f.write("## Breakdown\n\n")
        f.write(f"- **arXiv papers:** {arxiv_html} pairs\n")
        f.write(f"- **Law review articles:** {law_html} pairs\n\n")
        f.write("## Usage\n\n")
        f.write("Each pair consists of:\n")
        f.write("- `{basename}.html` - Full-text article in HTML format\n")
        f.write("- `{basename}.pdf` - Corresponding PDF file\n\n")
        f.write("These pairs will be used for HTML-PDF paragraph matching to generate ")
        f.write("ground truth labels for DoclingBERT v3 training.\n")

    print(f"\n📄 README created: {readme}")
    print(f"\n✅ Review folder ready! All {len(html_files)} pairs are in one location.")


if __name__ == "__main__":
    create_paired_review_folder()
