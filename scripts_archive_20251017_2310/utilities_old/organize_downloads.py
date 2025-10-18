#!/usr/bin/env python3
"""Identify and organize article pairs from Downloads folder."""

from collections import defaultdict
from pathlib import Path


def identify_journal_from_filename(filename: str) -> str:
    """Identify journal from filename or path."""
    lower = filename.lower()

    # Check for specific patterns
    if "bu_law_review" in lower or "bu law review" in lower:
        return "BU Law Review"
    elif "columbia" in lower and "law review" in lower:
        return "Columbia Law Review"
    elif "wisconsin" in lower and "law review" in lower:
        return "Wisconsin Law Review"
    elif "washington university law review" in lower or "washu" in lower:
        return "Washington University Law Review"
    elif "penn law review" in lower or "university of pennsylvania law review" in lower:
        return "Penn Law Review"
    elif "virginia law review" in lower:
        return "Virginia Law Review"
    elif "harvard law review" in lower:
        return "Harvard Law Review"
    elif "chicago law review" in lower or "university of chicago law review" in lower:
        return "University of Chicago Law Review"
    elif "texas law review" in lower:
        return "Texas Law Review"
    elif "california law review" in lower:
        return "California Law Review"
    elif "michigan law review" in lower:
        return "Michigan Law Review"
    elif "usc law review" in lower:
        return "USC Law Review"
    elif "supreme court review" in lower:
        return "Supreme Court Review"
    else:
        return "Unknown"


def find_pairs(downloads_dir: Path):
    """Find HTML-PDF pairs in Downloads directory."""
    html_files = list(downloads_dir.glob("*.html"))
    pdf_files = list(downloads_dir.glob("*.pdf"))

    # Create mapping by base name
    pairs = []
    unpaired_html = []
    unpaired_pdf = []

    for html_file in html_files:
        # Look for corresponding PDF
        html_stem = html_file.stem
        matching_pdf = None

        # Try exact match
        pdf_candidate = downloads_dir / f"{html_stem}.pdf"
        if pdf_candidate.exists():
            matching_pdf = pdf_candidate
        else:
            # Try fuzzy matching based on title similarity
            for pdf_file in pdf_files:
                # Remove common suffixes/variations
                html_clean = html_stem.lower().replace("_", " ").replace("-", " ")
                pdf_clean = pdf_file.stem.lower().replace("_", " ").replace("-", " ")

                # Check if substantial overlap
                if html_clean[:30] in pdf_clean or pdf_clean[:30] in html_clean:
                    matching_pdf = pdf_file
                    break

        if matching_pdf:
            pairs.append((html_file, matching_pdf))
        else:
            unpaired_html.append(html_file)

    # Find unpaired PDFs
    paired_pdfs = {pdf for _, pdf in pairs}
    unpaired_pdf = [pdf for pdf in pdf_files if pdf not in paired_pdfs]

    return pairs, unpaired_html, unpaired_pdf


def main():
    """Organize Downloads folder article pairs."""
    downloads_dir = Path.home() / "Downloads"

    pairs, unpaired_html, unpaired_pdf = find_pairs(downloads_dir)

    print("DOWNLOADS FOLDER ORGANIZATION")
    print("=" * 80)
    print(f"\nTotal HTML files: {len(list(downloads_dir.glob('*.html')))}")
    print(f"Total PDF files: {len(list(downloads_dir.glob('*.pdf')))}")
    print(f"\nMatched pairs: {len(pairs)}")
    print(f"Unpaired HTML: {len(unpaired_html)}")
    print(f"Unpaired PDF: {len(unpaired_pdf)}")

    # Group pairs by journal
    by_journal = defaultdict(list)
    for html_file, pdf_file in pairs:
        journal = identify_journal_from_filename(html_file.name)
        by_journal[journal].append((html_file, pdf_file))

    print(f"\n\n{'=' * 80}")
    print("PAIRS BY JOURNAL")
    print("=" * 80)

    for journal in sorted(by_journal.keys()):
        pairs_list = by_journal[journal]
        print(f"\n{journal}: {len(pairs_list)} pairs")
        for html_file, pdf_file in pairs_list:
            print(f"  HTML: {html_file.name[:60]}")
            print(f"  PDF:  {pdf_file.name[:60]}")
            print()

    # Show unpaired files
    if unpaired_html:
        print(f"\n{'=' * 80}")
        print(f"UNPAIRED HTML FILES ({len(unpaired_html)})")
        print("=" * 80)
        for html_file in unpaired_html[:10]:
            print(f"  {html_file.name}")

    if unpaired_pdf:
        print(f"\n{'=' * 80}")
        print(f"UNPAIRED PDF FILES ({len(unpaired_pdf)})")
        print("=" * 80)
        for pdf_file in unpaired_pdf[:10]:
            print(f"  {pdf_file.name}")


if __name__ == "__main__":
    main()
