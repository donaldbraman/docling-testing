#!/usr/bin/env python3
"""Remove abstract-only HTML-PDF pairs from the corpus."""

import csv
import shutil
from pathlib import Path


def remove_abstract_only_pairs():
    """Archive abstract-only pairs to keep corpus clean."""
    # Paths
    categorization_file = Path("data/html_categorization_results.csv")
    html_dir = Path("data/raw_html")
    pdf_dir = Path("data/raw_pdf")

    # Archive directories
    archive_dir = Path("data/archived_abstract_only")
    archive_html = archive_dir / "html"
    archive_pdf = archive_dir / "pdf"
    archive_html.mkdir(parents=True, exist_ok=True)
    archive_pdf.mkdir(parents=True, exist_ok=True)

    print("📦 Removing abstract-only pairs from corpus...\n")

    # Read categorization results
    abstract_only = []
    full_text = []

    with open(categorization_file) as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["category"] == "abstract_only":
                abstract_only.append(row["basename"])
            else:
                full_text.append(row["basename"])

    print(f"Found {len(abstract_only)} abstract-only pairs to archive")
    print(f"Found {len(full_text)} full-text pairs to keep\n")

    # Archive abstract-only files
    archived_html_count = 0
    archived_pdf_count = 0
    missing_html = []
    missing_pdf = []

    for basename in abstract_only:
        html_file = html_dir / f"{basename}.html"
        pdf_file = pdf_dir / f"{basename}.pdf"

        # Archive HTML
        if html_file.exists():
            shutil.move(str(html_file), str(archive_html / f"{basename}.html"))
            archived_html_count += 1
        else:
            missing_html.append(basename)

        # Archive PDF
        if pdf_file.exists():
            shutil.move(str(pdf_file), str(archive_pdf / f"{basename}.pdf"))
            archived_pdf_count += 1
        else:
            missing_pdf.append(basename)

    # Summary report
    print("=" * 70)
    print("CLEANUP SUMMARY")
    print("=" * 70)
    print(f"\n✅ Archived {archived_html_count} HTML files to: {archive_html}")
    print(f"✅ Archived {archived_pdf_count} PDF files to: {archive_pdf}")

    if missing_html:
        print(f"\n⚠️  {len(missing_html)} HTML files were already missing")
    if missing_pdf:
        print(f"⚠️  {len(missing_pdf)} PDF files were already missing")

    # Count remaining files
    remaining_html = len(list(html_dir.glob("*.html")))
    remaining_pdf = len(list(pdf_dir.glob("*.pdf")))

    print("\n📊 Remaining corpus:")
    print(f"   - HTML files: {remaining_html}")
    print(f"   - PDF files: {remaining_pdf}")
    print(f"   - Expected: {len(full_text)} full-text pairs + arxiv pairs")

    # Verify arxiv files are intact
    arxiv_html = len(list(html_dir.glob("arxiv_*.html")))
    arxiv_pdf = len(list(pdf_dir.glob("arxiv_*.pdf")))
    print("\n✅ arXiv papers preserved:")
    print(f"   - HTML: {arxiv_html}")
    print(f"   - PDF: {arxiv_pdf}")

    # Save cleanup report
    report_file = archive_dir / "CLEANUP_REPORT.md"
    with open(report_file, "w") as f:
        f.write("# Abstract-Only Pairs Cleanup Report\n\n")
        f.write(f"**Date:** {Path.cwd()}\n\n")
        f.write("## Summary\n\n")
        f.write(f"- Archived HTML files: {archived_html_count}\n")
        f.write(f"- Archived PDF files: {archived_pdf_count}\n")
        f.write(f"- Remaining HTML files: {remaining_html}\n")
        f.write(f"- Remaining PDF files: {remaining_pdf}\n")
        f.write(f"- arXiv HTML preserved: {arxiv_html}\n")
        f.write(f"- arXiv PDF preserved: {arxiv_pdf}\n\n")
        f.write("## Why These Were Archived\n\n")
        f.write("These HTML files contained only abstracts and metadata, not full article text. ")
        f.write(
            "They had very low Jaccard similarity scores (~2-30%) with their corresponding PDFs "
        )
        f.write("because they lacked the article body content.\n\n")
        f.write("## Restoration\n\n")
        f.write("To restore these files, move them back from `data/archived_abstract_only/` to ")
        f.write("`data/raw_html/` and `data/raw_pdf/`.\n")

    print(f"\n📄 Cleanup report saved to: {report_file}")
    print("\n✅ Cleanup complete! Corpus now contains only full-text HTML-PDF pairs.")


if __name__ == "__main__":
    remove_abstract_only_pairs()
