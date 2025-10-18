#!/usr/bin/env python3
"""Remove HTML files that don't have matching PDF files."""

import shutil
from pathlib import Path


def remove_unpaired_html():
    """Archive HTML files without matching PDFs (and any PDFs without HTML)."""
    html_dir = Path("data/raw_html")
    pdf_dir = Path("data/raw_pdf")

    # Single archive directory for both HTML and PDF
    archive_dir = Path("data/archived_unpaired")
    archive_dir.mkdir(parents=True, exist_ok=True)

    print("🔍 Finding unpaired HTML and PDF files...\n")

    # Find HTML files without matching PDFs
    unpaired_html = []
    for html_file in html_dir.glob("*.html"):
        pdf_file = pdf_dir / f"{html_file.stem}.pdf"
        if not pdf_file.exists():
            unpaired_html.append(html_file)

    # Find PDF files without matching HTML
    unpaired_pdf = []
    for pdf_file in pdf_dir.glob("*.pdf"):
        html_file = html_dir / f"{pdf_file.stem}.html"
        if not html_file.exists():
            unpaired_pdf.append(pdf_file)

    print(f"Found {len(unpaired_html)} HTML files without matching PDFs")
    print(f"Found {len(unpaired_pdf)} PDF files without matching HTML\n")

    if not unpaired_html and not unpaired_pdf:
        print("✅ All files are properly paired!")
        return

    # Show breakdown
    arxiv_unpaired_html = [f for f in unpaired_html if f.stem.startswith("arxiv_")]
    law_review_unpaired_html = [f for f in unpaired_html if not f.stem.startswith("arxiv_")]
    arxiv_unpaired_pdf = [f for f in unpaired_pdf if f.stem.startswith("arxiv_")]
    law_review_unpaired_pdf = [f for f in unpaired_pdf if not f.stem.startswith("arxiv_")]

    print(f"  Unpaired HTML - arXiv: {len(arxiv_unpaired_html)}")
    print(f"  Unpaired HTML - Law reviews: {len(law_review_unpaired_html)}")
    print(f"  Unpaired PDF - arXiv: {len(arxiv_unpaired_pdf)}")
    print(f"  Unpaired PDF - Law reviews: {len(law_review_unpaired_pdf)}\n")

    # Archive unpaired files (both HTML and PDF in same directory)
    for html_file in unpaired_html:
        shutil.move(str(html_file), str(archive_dir / html_file.name))

    for pdf_file in unpaired_pdf:
        shutil.move(str(pdf_file), str(archive_dir / pdf_file.name))

    print("=" * 70)
    print("CLEANUP SUMMARY")
    print("=" * 70)
    print(
        f"\n✅ Archived {len(unpaired_html)} unpaired HTML files and {len(unpaired_pdf)} unpaired PDF files"
    )
    print(f"   Location: {archive_dir}")

    # Count remaining
    remaining_html = len(list(html_dir.glob("*.html")))
    remaining_pdf = len(list(pdf_dir.glob("*.pdf")))

    print("\n📊 Final corpus (perfectly paired):")
    print(f"   - HTML files: {remaining_html}")
    print(f"   - PDF files: {remaining_pdf}")
    print(f"   - Matched pairs: {remaining_html}")  # Should equal remaining_pdf

    # Breakdown
    arxiv_html = len(list(html_dir.glob("arxiv_*.html")))
    arxiv_pdf = len(list(pdf_dir.glob("arxiv_*.pdf")))
    law_html = remaining_html - arxiv_html
    law_pdf = remaining_pdf - arxiv_pdf

    print(f"\n   arXiv pairs: {arxiv_html}")
    print(f"   Law review pairs: {law_html}")

    # Save report
    report_file = archive_dir / "CLEANUP_REPORT.md"
    with open(report_file, "w") as f:
        f.write("# Unpaired Files Cleanup Report\n\n")
        f.write("## Summary\n\n")
        f.write(f"- Archived HTML files: {len(unpaired_html)}\n")
        f.write(f"  - arXiv: {len(arxiv_unpaired_html)}\n")
        f.write(f"  - Law reviews: {len(law_review_unpaired_html)}\n")
        f.write(f"- Archived PDF files: {len(unpaired_pdf)}\n")
        f.write(f"  - arXiv: {len(arxiv_unpaired_pdf)}\n")
        f.write(f"  - Law reviews: {len(law_review_unpaired_pdf)}\n\n")
        f.write("## Why These Were Archived\n\n")
        f.write("These files had no matching pair (HTML or PDF), making them unusable for ")
        f.write("HTML-PDF paragraph matching in training data generation. All files are archived ")
        f.write("together in a single directory for easy review.\n\n")
        f.write("## Archived Files\n\n")
        f.write("### Unpaired HTML\n\n")
        for html_file in sorted(unpaired_html):
            f.write(f"- {html_file.name}\n")
        f.write("\n### Unpaired PDF\n\n")
        for pdf_file in sorted(unpaired_pdf):
            f.write(f"- {pdf_file.name}\n")

    print(f"\n📄 Report saved to: {report_file}")
    print("\n✅ Cleanup complete! All remaining files are perfectly paired.")


if __name__ == "__main__":
    remove_unpaired_html()
