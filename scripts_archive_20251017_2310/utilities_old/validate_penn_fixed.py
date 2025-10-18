#!/usr/bin/env python3
"""Validate Penn pairs with FIXED extraction from .entry-content."""

import re
from pathlib import Path

from bs4 import BeautifulSoup
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import LayoutOptions, PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption


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


def extract_paragraphs_from_penn_html(html_path: Path) -> list[str]:
    """Extract paragraphs from Penn HTML (from .entry-content section)."""
    with open(html_path, encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    # Remove script and style
    for script in soup(["script", "style"]):
        script.decompose()

    paragraphs = []

    # Penn uses WordPress .entry-content for article content
    entry_content = soup.find(class_=re.compile(r"entry-content", re.I))

    if entry_content:
        # Extract from entry-content section
        for p in entry_content.find_all("p"):
            text = p.get_text()
            text = re.sub(r"\s+", " ", text).strip()
            if len(text) > 50:
                paragraphs.append(text.lower())
    else:
        # Fallback to all <p> tags
        print("  ⚠️  No .entry-content found, using all <p> tags")
        for p in soup.find_all("p"):
            text = p.get_text()
            text = re.sub(r"\s+", " ", text).strip()
            if len(text) > 50:
                paragraphs.append(text.lower())

    return paragraphs


def extract_paragraphs_from_pdf(pdf_path: Path) -> list[str]:
    """Extract paragraphs from PDF using LayoutOptions."""
    pipeline = PdfPipelineOptions(
        layout_options=LayoutOptions(),
        generate_parsed_pages=True,
        generate_page_images=True,
        images_scale=1.0,
    )

    converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline)}
    )

    result = converter.convert(str(pdf_path))

    paragraphs = []
    for item, _level in result.document.iterate_items():
        if hasattr(item, "text") and item.text:
            text = item.text
            text = re.sub(r"\s+", " ", text).strip()
            if len(text) > 20:
                paragraphs.append(text.lower())

    return paragraphs


def calculate_jaccard(html_paragraphs: list[str], pdf_paragraphs: list[str]) -> float:
    """Calculate Jaccard similarity."""
    html_text = " ".join(html_paragraphs)
    pdf_text = " ".join(pdf_paragraphs)

    html_norm = normalize_text(html_text)
    pdf_norm = normalize_text(pdf_text)

    html_words = get_word_set(html_norm)
    pdf_words = get_word_set(pdf_norm)

    if not html_words or not pdf_words:
        return 0.0

    intersection = html_words & pdf_words
    union = html_words | pdf_words
    return (len(intersection) / len(union)) * 100 if union else 0.0


def validate_penn_pairs():
    """Validate Penn pairs with FIXED extraction."""
    downloads = Path.home() / "Downloads"

    penn_pairs = [
        (
            downloads / "Memory, Invisibility, & Power - Penn Law Review.html",
            downloads / "Memory Invisibility & Power.pdf",
            "Memory, Invisibility, & Power",
        ),
        (
            downloads
            / "Ordinary Public Meaning & Habeas Power to Review State Convictions - Penn Law Review.html",
            downloads / "Ordinary Public Meaning & Habeas Power to Review State Conviction.pdf",
            "Ordinary Public Meaning & Habeas",
        ),
        (
            downloads
            / "Trump v. United States and the Separation of Powers - Penn Law Review.html",
            downloads / "Trump v. United States and the Separation of Powers.pdf",
            "Trump v. United States",
        ),
        (
            downloads
            / "Common-Law Limits on Firearms Purchases by Minors_ The Original Understanding - Penn Law Review.html",
            downloads / "Common-Law Limits on Firearms Purchases by Minors_ The Original U.pdf",
            "Firearms Purchases by Minors",
        ),
        (
            downloads / "Against The Sliding Scale - Penn Law Review.html",
            downloads / "Against the Sliding Scale.pdf",
            "Against the Sliding Scale",
        ),
    ]

    print("🔍 Validating Penn pairs with FIXED extraction (.entry-content)\n")
    print(f"Found {len(penn_pairs)} Penn pairs\n")

    results = []

    for html_file, pdf_file, title in penn_pairs:
        if not html_file.exists() or not pdf_file.exists():
            print(f"⚠️  Files not found: {title}")
            continue

        print(f"\n{'=' * 70}")
        print(f"Testing: {title}")
        print(f"{'=' * 70}")

        # Extract paragraphs
        print("  Extracting from HTML (.entry-content)...")
        html_paragraphs = extract_paragraphs_from_penn_html(html_file)
        print(f"    Found {len(html_paragraphs)} paragraphs")

        print("  Extracting from PDF...")
        pdf_paragraphs = extract_paragraphs_from_pdf(pdf_file)
        print(f"    Found {len(pdf_paragraphs)} paragraphs")

        # Calculate Jaccard
        jaccard = calculate_jaccard(html_paragraphs, pdf_paragraphs)

        # Word counts
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

    print(f"\n{'=' * 70}")
    print(f"OVERALL: {len(accepted)}/{len(results)} pairs passed validation")

    return results


if __name__ == "__main__":
    validate_penn_pairs()
