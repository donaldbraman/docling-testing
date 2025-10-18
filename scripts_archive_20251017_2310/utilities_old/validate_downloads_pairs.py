#!/usr/bin/env python3
"""Validate BU and Harvard pairs from Downloads folder."""

import re
from pathlib import Path

from bs4 import BeautifulSoup
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import OcrMacOptions, PdfPipelineOptions
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
    """Extract all paragraph text from PDF using Docling with OCR."""
    print(f"    Using docling with OCR to extract from {pdf_path.name}...")

    # Configure OCR options for reliable extraction
    ocr_options = OcrMacOptions(force_full_page_ocr=True)

    # Configure pipeline with OCR enabled
    pipeline = PdfPipelineOptions(
        do_ocr=True,
        ocr_options=ocr_options,
        generate_page_images=True,
        images_scale=1.0,
    )

    # Create converter with OCR pipeline
    converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline)}
    )

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


def validate_downloads_pairs():
    """Validate BU and Harvard pairs from Downloads folder."""
    downloads = Path.home() / "Downloads"

    # Find BU online essay pairs
    bu_html_files = sorted([f for f in downloads.glob("bu_law_review_online_*.html")])

    # Find Harvard pairs
    harvard_html_files = sorted(
        [
            f
            for f in downloads.glob("harvard_law_review_*.html")
            if "Background_Principles" not in f.name  # Skip old one
        ]
    )

    all_pairs = []

    # BU pairs
    for html_file in bu_html_files:
        pdf_file = html_file.with_suffix(".pdf")
        if pdf_file.exists():
            title = html_file.stem.replace("bu_law_review_online_", "").replace("_", " ").title()
            all_pairs.append(("BU", html_file, pdf_file, title))

    # Harvard pairs
    for html_file in harvard_html_files:
        pdf_file = html_file.with_suffix(".pdf")
        if pdf_file.exists():
            title = html_file.stem.replace("harvard_law_review_", "").replace("_", " ").title()
            all_pairs.append(("Harvard", html_file, pdf_file, title))

    print("🔍 Validating newly collected pairs from Downloads...\n")
    print(f"Found {len([p for p in all_pairs if p[0] == 'BU'])} BU online essay pairs")
    print(f"Found {len([p for p in all_pairs if p[0] == 'Harvard'])} Harvard pairs\n")

    results = []

    for source, html_file, pdf_file, title in all_pairs:
        if len(title) > 50:
            title = title[:47] + "..."

        print(f"\n{'=' * 70}")
        print(f"Testing: {source} - {title}")
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
                "source": source,
                "title": title,
                "html_file": html_file.name,
                "pdf_file": pdf_file.name,
                "jaccard": jaccard,
                "html_words": html_words,
                "pdf_words": pdf_words,
                "status": "ACCEPT" if jaccard >= 75 else "REJECT",
            }
        )

    # Summary by source
    print(f"\n\n{'=' * 70}")
    print("VALIDATION SUMMARY")
    print(f"{'=' * 70}\n")

    for source in ["BU", "Harvard"]:
        source_results = [r for r in results if r["source"] == source]
        if not source_results:
            continue

        accepted = [r for r in source_results if r["status"] == "ACCEPT"]
        rejected = [r for r in source_results if r["status"] == "REJECT"]

        print(f"\n{source.upper()}:")
        print(f"  ✅ Accepted (≥75%): {len(accepted)}")
        for r in accepted:
            print(f"     {r['jaccard']:5.1f}% - {r['title']}")

        if rejected:
            print(f"  ❌ Rejected (<75%): {len(rejected)}")
            for r in rejected:
                print(f"     {r['jaccard']:5.1f}% - {r['title']}")

        if accepted:
            avg = sum(r["jaccard"] for r in accepted) / len(accepted)
            print(f"  📊 Average quality (accepted): {avg:.1f}%")

    # Overall summary
    all_accepted = [r for r in results if r["status"] == "ACCEPT"]
    print(f"\n{'=' * 70}")
    print(f"OVERALL: {len(all_accepted)}/{len(results)} pairs passed validation")
    if all_accepted:
        overall_avg = sum(r["jaccard"] for r in all_accepted) / len(all_accepted)
        print(f"Overall average quality: {overall_avg:.1f}%")

    return results


if __name__ == "__main__":
    validate_downloads_pairs()
