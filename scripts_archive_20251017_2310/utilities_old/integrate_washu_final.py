#!/usr/bin/env python3
"""Integrate validated WashU HTML-PDF pairs into corpus."""

import re
import shutil
from pathlib import Path


def slugify(text: str) -> str:
    """Convert text to filename-safe slug."""
    text = re.sub(r"[^\w\s-]", "", text.lower())
    text = re.sub(r"[-\s]+", "_", text)
    return text.strip("_")


def integrate_washu_pairs():
    """Integrate 5 validated WashU pairs into corpus."""
    downloads = Path.home() / "Downloads"
    html_dir = Path("data/raw_html")
    pdf_dir = Path("data/raw_pdf")

    html_dir.mkdir(parents=True, exist_ok=True)
    pdf_dir.mkdir(parents=True, exist_ok=True)

    print("📥 Integrating Washington University Law Review pairs...\n")

    # Validated pairs with correct pairings (97.0% avg quality)
    pairs = [
        (
            "Cliff Running – Washington University Law Review.html",
            "13_Fox-Ortman_FINAL-08.29.25-.pdf",
            "Cliff Running",
            96.2,
        ),
        (
            "Drug Dealing_ Making Public Pharma Work – Washington University Law Review.html",
            "11_Agrawal-et-al_FINAL-09.02.25-1.pdf",
            "Drug Dealing Making Public Pharma Work",
            98.1,
        ),
        (
            "Personal Jurisdiction and Federalism – Washington University Law Review.html",
            "10_Dodson_FINAL-08.12.25-.pdf",
            "Personal Jurisdiction and Federalism",
            96.3,
        ),
        (
            "The Consequences of Ending Birthright Citizenship – Washington University Law Review.html",
            "14_Hamburger_FINAL-08.30.25.pdf",
            "The Consequences of Ending Birthright Citizenship",
            96.0,
        ),
        (
            "When is Discrimination Harmful_ – Washington University Law Review.html",
            "12_Sperino_FINAL-08.12.25-.pdf",
            "When is Discrimination Harmful",
            98.6,
        ),
    ]

    print(f"Processing {len(pairs)} high-quality pairs (97.0% avg)...\n")

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
        basename = f"washu_law_review_{slugify(title)}"

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
    print(f"\n✅ Added {len(pairs)} Washington University Law Review pairs")
    print("   Average quality: 97.0%")
    print("   Location: data/raw_html/ and data/raw_pdf/")

    # Count total corpus
    total_html = len(list(html_dir.glob("*.html")))
    total_pdf = len(list(pdf_dir.glob("*.pdf")))

    print("\n📊 Updated corpus:")
    print(f"   HTML files: {total_html}")
    print(f"   PDF files:  {total_pdf}")

    print("\n🎯 Next step: Run corpus building to generate training data")


if __name__ == "__main__":
    integrate_washu_pairs()
