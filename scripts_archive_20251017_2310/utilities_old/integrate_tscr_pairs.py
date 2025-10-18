#!/usr/bin/env python3
"""Integrate validated Supreme Court Review pairs into corpus."""

import re
import shutil
from pathlib import Path


def slugify(text: str) -> str:
    """Convert text to filename-safe slug."""
    text = re.sub(r"[^\w\s-]", "", text.lower())
    text = re.sub(r"[-\s]+", "_", text)
    return text.strip("_")


def integrate_tscr_pairs():
    """Integrate 3 Supreme Court Review pairs."""
    downloads = Path.home() / "Downloads"
    html_dir = Path("data/raw_html")
    pdf_dir = Path("data/raw_pdf")

    html_dir.mkdir(parents=True, exist_ok=True)
    pdf_dir.mkdir(parents=True, exist_ok=True)

    print("📥 Integrating Supreme Court Review pairs...\n")

    # Validated pairs with quality scores
    pairs = [
        (
            "Purdue Pharma and the New Bankruptcy Exceptionalism_ The Supreme Court Review_ Vol 2024.html",
            "Purdue Pharma and the New Bankruptcy Exceptionalism_ The Supreme Court Review_ Vol 2024.pdf",
            "Purdue Pharma and the New Bankruptcy Exceptionalism",
            92.5,
        ),
        (
            "Fear of Balancing_ The Supreme Court Review_ Vol 2024.html",
            "Fear of Balancing_ The Supreme Court Review_ Vol 2024.pdf",
            "Fear of Balancing",
            92.0,
        ),
        (
            "The Presidency After Trump v. United States_ The Supreme Court Review_ Vol 2024.html",
            "The Presidency After Trump v. United States_ The Supreme Court Review_ Vol 2024.pdf",
            "The Presidency After Trump v United States",
            91.0,
        ),
    ]

    print(f"Processing {len(pairs)} high-quality pairs (91.8% avg)...\n")

    for html_filename, pdf_filename, title, jaccard in pairs:
        html_src = downloads / html_filename
        pdf_src = downloads / pdf_filename

        if not html_src.exists():
            print(f"⚠️  HTML not found: {html_filename}")
            continue
        if not pdf_src.exists():
            print(f"⚠️  PDF not found: {pdf_filename}")
            continue

        # Generate basename
        basename = f"supreme_court_review_{slugify(title)}"

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

    print("=" * 70)
    print("INTEGRATION COMPLETE")
    print("=" * 70)
    print(f"\n✅ Added {len(pairs)} Supreme Court Review pairs")
    print("   Average quality: 91.8%")
    print("   Location: data/raw_html/ and data/raw_pdf/")

    # Count total corpus
    total_html = len(list(html_dir.glob("*.html")))
    total_pdf = len(list(pdf_dir.glob("*.pdf")))

    print("\n📊 Updated corpus:")
    print(f"   HTML files: {total_html}")
    print(f"   PDF files:  {total_pdf}")

    print("\n🎯 Next step: Validate entire corpus with paragraph matching")


if __name__ == "__main__":
    integrate_tscr_pairs()
