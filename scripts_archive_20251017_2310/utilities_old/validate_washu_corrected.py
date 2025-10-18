#!/usr/bin/env python3
"""Validate WashU HTML-PDF pairs with CORRECT pairings using Docling."""

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


def extract_all_paragraphs_from_html(html_path: Path) -> list[str]:
    """Extract all paragraph text from HTML (body + footnotes)."""
    with open(html_path, encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.decompose()

    paragraphs = []

    # Extract all <p> tags with substantial content
    for p in soup.find_all("p"):
        text = p.get_text()
        text = re.sub(r"\s+", " ", text).strip()
        if len(text) > 50:  # Filter very short paragraphs
            paragraphs.append(text.lower())

    return paragraphs


def extract_all_paragraphs_from_pdf(pdf_path: Path) -> list[str]:
    """Extract all paragraph text from PDF using Docling."""
    print(f"    Using docling to extract from {pdf_path.name}...")

    converter = DocumentConverter()
    result = converter.convert(str(pdf_path))

    paragraphs = []

    for item, _level in result.document.iterate_items():
        if hasattr(item, "text") and item.text:
            text = item.text
            text = re.sub(r"\s+", " ", text).strip()
            if len(text) > 20:  # Filter very short items
                paragraphs.append(text.lower())

    return paragraphs


def calculate_jaccard(html_paragraphs: list[str], pdf_paragraphs: list[str]) -> float:
    """Calculate Jaccard similarity between HTML and PDF content."""
    # Combine all paragraphs into single text
    html_text = " ".join(html_paragraphs)
    pdf_text = " ".join(pdf_paragraphs)

    # Normalize and get word sets
    html_norm = normalize_text(html_text)
    pdf_norm = normalize_text(pdf_text)

    html_words = get_word_set(html_norm)
    pdf_words = get_word_set(pdf_norm)

    if not html_words or not pdf_words:
        return 0.0

    # Calculate Jaccard
    intersection = html_words & pdf_words
    union = html_words | pdf_words
    return (len(intersection) / len(union)) * 100 if union else 0.0


def validate_washu_pairs():
    """Validate WashU pairs with CORRECT pairings."""
    downloads = Path.home() / "Downloads"

    # CORRECT pairings based on user's visual inspection
    matches = [
        (
            downloads / "Cliff Running – Washington University Law Review.html",
            downloads / "13_Fox-Ortman_FINAL-08.29.25-.pdf",
            "Cliff Running",
        ),
        (
            downloads
            / "Drug Dealing_ Making Public Pharma Work – Washington University Law Review.html",
            downloads / "11_Agrawal-et-al_FINAL-09.02.25-1.pdf",
            "Drug Dealing",
        ),
        (
            downloads
            / "Personal Jurisdiction and Federalism – Washington University Law Review.html",
            downloads / "10_Dodson_FINAL-08.12.25-.pdf",
            "Personal Jurisdiction",
        ),
        (
            downloads
            / "The Consequences of Ending Birthright Citizenship – Washington University Law Review.html",
            downloads / "14_Hamburger_FINAL-08.30.25.pdf",
            "Birthright Citizenship",
        ),
        (
            downloads / "When is Discrimination Harmful_ – Washington University Law Review.html",
            downloads / "12_Sperino_FINAL-08.12.25-.pdf",
            "Discrimination Harmful",
        ),
    ]

    print("🔍 Validating WashU HTML-PDF pairs (CORRECTED pairings)...\n")
    print(f"Testing {len(matches)} pairs\n")

    results = []

    for html_file, pdf_file, title in matches:
        if not html_file.exists():
            print(f"⚠️  HTML file not found: {html_file.name}")
            continue
        if not pdf_file.exists():
            print(f"⚠️  PDF file not found: {pdf_file.name}")
            continue

        print(f"\n{'=' * 70}")
        print(f"Testing: {title}")
        print(f"{'=' * 70}")
        print(f"  HTML: {html_file.name}")
        print(f"  PDF:  {pdf_file.name}")

        # Extract paragraphs
        print("\n  Extracting from HTML...")
        html_paragraphs = extract_all_paragraphs_from_html(html_file)
        print(f"    Found {len(html_paragraphs)} paragraphs")

        print("  Extracting from PDF...")
        pdf_paragraphs = extract_all_paragraphs_from_pdf(pdf_file)
        print(f"    Found {len(pdf_paragraphs)} paragraphs")

        # Calculate Jaccard
        jaccard = calculate_jaccard(html_paragraphs, pdf_paragraphs)

        # Word counts (significant words only)
        html_words = len(get_word_set(normalize_text(" ".join(html_paragraphs))))
        pdf_words = len(get_word_set(normalize_text(" ".join(pdf_paragraphs))))

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
                "html_paras": len(html_paragraphs),
                "pdf_paras": len(pdf_paragraphs),
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
        print(f"   Add {len(accepted)} pairs. Consider investigating rejected pairs.")
    else:
        print("   No pairs meet 75% threshold.")

    return results


if __name__ == "__main__":
    validate_washu_pairs()
