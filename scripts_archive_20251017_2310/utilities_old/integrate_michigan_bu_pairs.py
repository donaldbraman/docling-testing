#!/usr/bin/env python3
"""Integrate validated Michigan and BU Online pairs into corpus."""

import re
import shutil
from pathlib import Path


def slugify(text: str) -> str:
    """Convert text to filename-safe slug."""
    text = re.sub(r"[^\w\s-]", "", text.lower())
    text = re.sub(r"[-\s]+", "_", text)
    return text.strip("_")


def integrate_michigan_pairs():
    """Integrate 5 Michigan Law Review pairs from html_pdf_pairs directory."""
    base_dir = Path("data/html_pdf_pairs")
    html_dir = Path("data/raw_html")
    pdf_dir = Path("data/raw_pdf")

    html_dir.mkdir(parents=True, exist_ok=True)
    pdf_dir.mkdir(parents=True, exist_ok=True)

    # Find Michigan directories
    michigan_dirs = sorted(
        [d for d in base_dir.iterdir() if d.is_dir() and "michigan" in d.name.lower()]
    )

    print("📥 Integrating Michigan Law Review pairs...\n")
    print(f"Found {len(michigan_dirs)} Michigan pairs (91.0% avg quality)\n")

    for pair_dir in michigan_dirs:
        html_files = list(pair_dir.glob("*.html"))
        pdf_files = list(pair_dir.glob("*.pdf"))

        if not html_files or not pdf_files:
            print(f"⚠️  Incomplete pair: {pair_dir.name}")
            continue

        html_src = html_files[0]
        pdf_src = pdf_files[0]

        # Use directory name as basename (already slugified)
        basename = pair_dir.name

        html_dest = html_dir / f"{basename}.html"
        pdf_dest = pdf_dir / f"{basename}.pdf"

        # Extract title for display
        title = pair_dir.name.replace("michigan_law_review_", "").replace("_", " ").title()
        if len(title) > 50:
            title = title[:47] + "..."

        print(f"✅ {title}")
        print(f"   → {basename}.html")
        print(f"   → {basename}.pdf")

        # Copy files
        shutil.copy(html_src, html_dest)
        shutil.copy(pdf_src, pdf_dest)
        print()

    return len(michigan_dirs)


def integrate_bu_pairs():
    """Integrate 5 BU Online pairs from Downloads."""
    downloads = Path.home() / "Downloads"
    html_dir = Path("data/raw_html")
    pdf_dir = Path("data/raw_pdf")

    html_dir.mkdir(parents=True, exist_ok=True)
    pdf_dir.mkdir(parents=True, exist_ok=True)

    # BU pairs with quality scores
    bu_pairs = [
        (
            "bu_law_review_online_building_new_constitutional_jerusalem.html",
            "bu_law_review_online_building_new_constitutional_jerusalem.pdf",
            "Building New Constitutional Jerusalem",
            93.1,
        ),
        (
            "bu_law_review_online_fourth_amendment_secure.html",
            "bu_law_review_online_fourth_amendment_secure.pdf",
            "Fourth Amendment Secure",
            95.9,
        ),
        (
            "bu_law_review_online_law_and_culture.html",
            "bu_law_review_online_law_and_culture.pdf",
            "Law and Culture",
            92.9,
        ),
        (
            "bu_law_review_online_nil_compliance.html",
            "bu_law_review_online_nil_compliance.pdf",
            "NIL Compliance",
            93.7,
        ),
        (
            "bu_law_review_online_reasonable_yet_suspicious.html",
            "bu_law_review_online_reasonable_yet_suspicious.pdf",
            "Reasonable Yet Suspicious",
            95.5,
        ),
    ]

    print("\n📥 Integrating BU Law Review Online pairs...\n")
    print(f"Found {len(bu_pairs)} BU pairs (94.2% avg quality)\n")

    for html_filename, pdf_filename, title, jaccard in bu_pairs:
        html_src = downloads / html_filename
        pdf_src = downloads / pdf_filename

        if not html_src.exists():
            print(f"⚠️  HTML not found: {html_filename}")
            continue
        if not pdf_src.exists():
            print(f"⚠️  PDF not found: {pdf_filename}")
            continue

        # Use filename basename (already slugified)
        basename = html_filename.replace(".html", "")

        html_dest = html_dir / f"{basename}.html"
        pdf_dest = pdf_dir / f"{basename}.pdf"

        print(f"✅ {title}")
        print(f"   Quality: {jaccard:.1f}%")
        print(f"   → {basename}.html")
        print(f"   → {basename}.pdf")

        # Copy files
        shutil.copy(html_src, html_dest)
        shutil.copy(pdf_src, pdf_dest)
        print()

    return len(bu_pairs)


def main():
    """Integrate Michigan and BU pairs into corpus."""
    michigan_count = integrate_michigan_pairs()
    bu_count = integrate_bu_pairs()

    # Count total corpus
    html_dir = Path("data/raw_html")
    pdf_dir = Path("data/raw_pdf")

    total_html = len(list(html_dir.glob("*.html")))
    total_pdf = len(list(pdf_dir.glob("*.pdf")))

    print("=" * 70)
    print("INTEGRATION COMPLETE")
    print("=" * 70)
    print(f"\n✅ Added {michigan_count} Michigan Law Review pairs (91.0% avg)")
    print(f"✅ Added {bu_count} BU Law Review Online pairs (94.2% avg)")
    print(f"   Total added: {michigan_count + bu_count} pairs")

    print("\n📊 Updated corpus:")
    print(f"   HTML files: {total_html}")
    print(f"   PDF files:  {total_pdf}")

    print("\n🎯 Next step: Run corpus building to generate training data")


if __name__ == "__main__":
    main()
