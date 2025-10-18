#!/usr/bin/env python3
"""Integrate Washington University Law Review downloads into corpus."""

import re
import shutil
from pathlib import Path

import pypdf
from bs4 import BeautifulSoup


def normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\d+", "", text)
    return text.strip()


def get_word_set(text: str, min_length: int = 4) -> set:
    """Get set of significant words from text."""
    words = text.split()
    return {w for w in words if len(w) >= min_length}


def extract_text_from_html(html_path: Path) -> str:
    """Extract clean text from HTML file."""
    with open(html_path, encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    for script in soup(["script", "style"]):
        script.decompose()

    text = soup.get_text()
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = " ".join(chunk for chunk in chunks if chunk)
    return text.lower()


def calculate_jaccard(html_path: Path, pdf_path: Path) -> float:
    """Calculate Jaccard similarity between HTML and PDF."""
    # Extract HTML text
    html_text = extract_text_from_html(html_path)

    # Extract PDF text
    pdf_reader = pypdf.PdfReader(pdf_path)
    pdf_text = ""
    for page in pdf_reader.pages:
        pdf_text += page.extract_text()
    pdf_text = pdf_text.lower()

    # Normalize
    html_norm = normalize_text(html_text)
    pdf_norm = normalize_text(pdf_text)

    # Get word sets
    html_words = get_word_set(html_norm)
    pdf_words = get_word_set(pdf_norm)

    if not html_words or not pdf_words:
        return 0.0

    # Calculate Jaccard
    intersection = html_words & pdf_words
    union = html_words | pdf_words
    return (len(intersection) / len(union)) * 100 if union else 0.0


def slugify(text: str) -> str:
    """Convert text to filename-safe slug."""
    # Remove special characters, convert to lowercase
    text = re.sub(r"[^\w\s-]", "", text.lower())
    # Replace spaces with underscores
    text = re.sub(r"[-\s]+", "_", text)
    return text.strip("_")


def integrate_washu_downloads():
    """Integrate WashU downloads into corpus."""
    downloads_dir = Path.home() / "Downloads"
    html_dir = Path("data/raw_html")
    pdf_dir = Path("data/raw_pdf")
    archive_dir = Path("data/archived_low_quality")
    archive_dir.mkdir(parents=True, exist_ok=True)

    print("📥 Integrating Washington University Law Review downloads...\n")

    # Find WashU files
    html_files = list(downloads_dir.glob("*Washington University Law Review.html"))
    pdf_files = sorted(
        [
            f
            for f in downloads_dir.glob("*.pdf")
            if f.stem.split("_")[0].isdigit()
            and int(f.stem.split("_")[0]) >= 10
            and int(f.stem.split("_")[0]) <= 20
        ]
    )

    print(f"Found {len(html_files)} HTML files")
    print(f"Found {len(pdf_files)} PDF files\n")

    # Match HTML to PDF by extracting titles
    pairs = []

    for html_file in html_files:
        # Extract title from HTML filename
        title = html_file.stem.replace(" – Washington University Law Review", "")

        # Find matching PDF by checking if title words appear in PDF filename
        title_words = set(slugify(title).split("_"))
        best_match = None
        best_score = 0

        for pdf_file in pdf_files:
            pdf_words = set(slugify(pdf_file.stem).split("_"))
            overlap = len(title_words & pdf_words)
            if overlap > best_score:
                best_score = overlap
                best_match = pdf_file

        if best_match and best_score >= 2:  # At least 2 words match
            pairs.append((html_file, best_match, title))

    print(f"Matched {len(pairs)} HTML-PDF pairs\n")

    # Process pairs
    results = []

    for html_file, pdf_file, title in pairs:
        # Generate basename
        basename = f"washu_law_review_{slugify(title)}"

        print(f"Processing: {title[:60]}...")

        # Calculate quality
        jaccard = calculate_jaccard(html_file, pdf_file)
        print(f"  Jaccard: {jaccard:.1f}%")

        # Determine destination
        if jaccard >= 75:
            dest_html = html_dir / f"{basename}.html"
            dest_pdf = pdf_dir / f"{basename}.pdf"
            status = "ACCEPTED"
            print(f"  Status: ✅ {status}")
        else:
            dest_html = archive_dir / f"{basename}.html"
            dest_pdf = archive_dir / f"{basename}.pdf"
            status = "REJECTED"
            print(f"  Status: ❌ {status} (< 75%)")

        # Copy files
        shutil.copy(html_file, dest_html)
        shutil.copy(pdf_file, dest_pdf)

        results.append(
            {
                "title": title,
                "basename": basename,
                "jaccard": jaccard,
                "status": status,
            }
        )

        print()

    # Summary
    accepted = [r for r in results if r["status"] == "ACCEPTED"]
    rejected = [r for r in results if r["status"] == "REJECTED"]

    print("=" * 70)
    print("INTEGRATION SUMMARY")
    print("=" * 70)
    print(f"\n✅ Accepted (≥75%): {len(accepted)}")
    for r in accepted:
        print(f"   {r['jaccard']:5.1f}% - {r['title'][:50]}")

    if rejected:
        print(f"\n❌ Rejected (<75%): {len(rejected)}")
        for r in rejected:
            print(f"   {r['jaccard']:5.1f}% - {r['title'][:50]}")

    if accepted:
        avg_jaccard = sum(r["jaccard"] for r in accepted) / len(accepted)
        print(f"\n📊 Average quality of accepted: {avg_jaccard:.1f}%")

    print("\n📁 Files added to:")
    print("   Accepted: data/raw_html/ and data/raw_pdf/")
    if rejected:
        print("   Rejected: data/archived_low_quality/")

    print("\n✅ Integration complete!")
    print(f"   Total in corpus: {len(list(html_dir.glob('*.html')))} HTML files")


if __name__ == "__main__":
    integrate_washu_downloads()
