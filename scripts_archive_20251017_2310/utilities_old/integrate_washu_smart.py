#!/usr/bin/env python3
"""Integrate Washington University Law Review downloads with smart PDF title extraction."""

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
    for page in pdf_reader.pages[:10]:  # First 10 pages for speed
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


def extract_pdf_title(pdf_path: Path) -> str:
    """Extract title from PDF first page."""
    try:
        pdf_reader = pypdf.PdfReader(pdf_path)
        first_page_text = pdf_reader.pages[0].extract_text()

        # Try to find title in first few lines
        lines = [line.strip() for line in first_page_text.split("\n") if line.strip()]

        # Often the title is in the first 5-10 lines, and is the longest line or in caps
        candidates = []
        for line in lines[:15]:
            if len(line) > 20 and len(line) < 150:  # Reasonable title length
                candidates.append(line)

        # Return the longest reasonable line as likely title
        if candidates:
            return max(candidates, key=len)
        return ""
    except:
        return ""


def slugify(text: str) -> str:
    """Convert text to filename-safe slug."""
    # Remove special characters, convert to lowercase
    text = re.sub(r"[^\w\s-]", "", text.lower())
    # Replace spaces/dashes with underscores
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

    # Find WashU HTML files
    html_files = []
    for f in downloads_dir.glob("*.html"):
        if "washington university law review" in f.name.lower():
            html_files.append(f)

    # Find numbered PDFs (10-14)
    pdf_files = sorted([f for f in downloads_dir.glob("[0-9][0-9]_*.pdf")])

    print(f"Found {len(html_files)} HTML files")
    print(f"Found {len(pdf_files)} PDF files\n")

    if not html_files or not pdf_files:
        print("❌ No files found. Check Downloads folder.")
        return

    # List files and extract titles
    print("HTML files:")
    for i, html_file in enumerate(html_files, 1):
        title = html_file.stem.split(" – ")[0] if " – " in html_file.stem else html_file.stem
        print(f"  {i}. {title}")

    print("\nPDF files:")
    for i, pdf_file in enumerate(pdf_files, 1):
        pdf_title = extract_pdf_title(pdf_file)
        print(f"  {i}. {pdf_file.name[:40]}... → Title: {pdf_title[:60]}")

    # Try to match automatically by calculating Jaccard for all combinations
    print("\n🔍 Auto-matching by content similarity...\n")

    pairs = []
    used_pdfs = set()

    for html_file in html_files:
        html_title = html_file.stem.split(" – ")[0] if " – " in html_file.stem else html_file.stem

        best_match = None
        best_jaccard = 0

        # Try each unused PDF
        for pdf_file in pdf_files:
            if pdf_file in used_pdfs:
                continue

            jaccard = calculate_jaccard(html_file, pdf_file)
            if jaccard > best_jaccard:
                best_jaccard = jaccard
                best_match = pdf_file

        if best_match and best_jaccard >= 50:  # Reasonable threshold for matching
            pairs.append((html_file, best_match, html_title, best_jaccard))
            used_pdfs.add(best_match)
            print(f"✓ Matched: {html_title[:50]} → {best_match.name} ({best_jaccard:.1f}%)")

    if not pairs:
        print("\n❌ Could not auto-match files. Manual matching needed.")
        return

    print(f"\n\nMatched {len(pairs)} pairs. Processing...\n")

    # Process pairs
    results = []

    for html_file, pdf_file, title, initial_jaccard in pairs:
        # Generate basename
        basename = f"washu_law_review_{slugify(title)}"

        print(f"Processing: {title[:60]}...")
        print(f"  Initial match quality: {initial_jaccard:.1f}%")

        # Determine destination
        if initial_jaccard >= 75:
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
                "jaccard": initial_jaccard,
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
    print(f"   Total in corpus now: {len(list(html_dir.glob('*.html')))} HTML files")


if __name__ == "__main__":
    integrate_washu_downloads()
