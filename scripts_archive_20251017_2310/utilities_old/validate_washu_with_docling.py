#!/usr/bin/env python3
"""Validate WashU HTML-PDF pairs using Docling (same as training pipeline)."""

import re
from pathlib import Path

from bs4 import BeautifulSoup
from docling.document_converter import DocumentConverter


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


def extract_text_from_pdf_with_docling(pdf_path: Path) -> str:
    """Extract text from PDF using Docling (same as training pipeline)."""
    print(f"    Using docling to extract from {pdf_path.name}...")
    converter = DocumentConverter()
    result = converter.convert(str(pdf_path))

    # Extract all text from document
    text_parts = []
    for item, _level in result.document.iterate_items():
        if hasattr(item, "text") and item.text:
            text_parts.append(item.text)

    return " ".join(text_parts).lower()


def calculate_jaccard(html_text: str, pdf_text: str) -> float:
    """Calculate Jaccard similarity."""
    html_norm = normalize_text(html_text)
    pdf_norm = normalize_text(pdf_text)

    html_words = get_word_set(html_norm)
    pdf_words = get_word_set(pdf_norm)

    if not html_words or not pdf_words:
        return 0.0

    intersection = html_words & pdf_words
    union = html_words | pdf_words
    return (len(intersection) / len(union)) * 100 if union else 0.0


def validate_washu_pairs():
    """Validate WashU pairs using Docling."""
    downloads = Path.home() / "Downloads"

    html_files = sorted(
        [
            f
            for f in downloads.glob("*.html")
            if "washington university law review" in f.name.lower()
        ]
    )
    pdf_files = sorted([f for f in downloads.glob("[0-9][0-9]_*.pdf")])

    print("🔍 Validating WashU HTML-PDF pairs using Docling...\n")
    print(f"Found {len(html_files)} HTML files")
    print(f"Found {len(pdf_files)} PDF files\n")

    # Test best matches based on visual inspection
    matches = [
        (html_files[3], pdf_files[3], "Cliff Running"),  # HTML 4 → PDF 4 (13_Fox-Ortman)
        (
            html_files[1],
            pdf_files[1],
            "Drug Dealing",
        ),  # HTML 2 → PDF 2 (11_Agrawal-et-al)
        (
            html_files[2],
            pdf_files[0],
            "Personal Jurisdiction",
        ),  # HTML 3 → PDF 1 (10_Dodson)
        (
            html_files[4],
            pdf_files[4],
            "Birthright Citizenship",
        ),  # HTML 5 → PDF 5 (14_Hamburger)
        (
            html_files[0],
            pdf_files[2],
            "Discrimination Harmful",
        ),  # HTML 1 → PDF 3 (12_Sperino)
    ]

    results = []

    for html_file, pdf_file, title in matches:
        print(f"\n{'=' * 70}")
        print(f"Testing: {title}")
        print(f"{'=' * 70}")
        print(f"  HTML: {html_file.name}")
        print(f"  PDF:  {pdf_file.name}")

        # Extract texts
        html_text = extract_text_from_html(html_file)
        pdf_text = extract_text_from_pdf_with_docling(pdf_file)

        # Calculate Jaccard
        jaccard = calculate_jaccard(html_text, pdf_text)

        # Word counts
        html_words = len(get_word_set(normalize_text(html_text)))
        pdf_words = len(get_word_set(normalize_text(pdf_text)))

        print("\n  Results:")
        print(f"    HTML words: {html_words:,}")
        print(f"    PDF words:  {pdf_words:,}")
        print(f"    Jaccard:    {jaccard:.1f}%")

        status = "✅ ACCEPT" if jaccard >= 75 else "❌ REJECT"
        print(f"    Status:     {status}")

        results.append(
            {
                "title": title,
                "html_file": html_file.name,
                "pdf_file": pdf_file.name,
                "jaccard": jaccard,
                "html_words": html_words,
                "pdf_words": pdf_words,
                "status": "ACCEPT" if jaccard >= 75 else "REJECT",
            }
        )

    # Summary
    print(f"\n\n{'=' * 70}")
    print("VALIDATION SUMMARY")
    print(f"{'=' * 70}\n")

    accepted = [r for r in results if r["status"] == "ACCEPT"]
    rejected = [r for r in results if r["status"] == "REJECT"]

    print(f"✅ Accepted (≥75%): {len(accepted)}")
    for r in accepted:
        print(f"   {r['jaccard']:5.1f}% - {r['title']}")

    if rejected:
        print(f"\n❌ Rejected (<75%): {len(rejected)}")
        for r in rejected:
            print(f"   {r['jaccard']:5.1f}% - {r['title']}")

    if accepted:
        avg = sum(r["jaccard"] for r in accepted) / len(accepted)
        print(f"\n📊 Average quality (accepted): {avg:.1f}%")

    print("\n🎯 Recommendation:")
    if len(accepted) >= 3:
        print(f"   Good quality! Add {len(accepted)} pairs to corpus.")
    elif len(accepted) > 0:
        print(f"   Only {len(accepted)} pairs meet threshold. Consider manual review.")
    else:
        print("   No pairs meet 75% threshold. These are likely abstract-only.")


if __name__ == "__main__":
    validate_washu_pairs()
