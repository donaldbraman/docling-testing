#!/usr/bin/env python3
"""Validate Supreme Court Review and additional Penn pairs from Downloads."""

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


def validate_tscr_penn_pairs():
    """Validate Supreme Court Review and additional Penn pairs."""
    downloads = Path.home() / "Downloads"

    print("🔍 Validating Supreme Court Review and Penn pairs from Downloads...\n")

    # Supreme Court Review pairs
    tscr_pairs = [
        (
            downloads
            / "Purdue Pharma and the New Bankruptcy Exceptionalism_ The Supreme Court Review_ Vol 2024.html",
            downloads
            / "Purdue Pharma and the New Bankruptcy Exceptionalism_ The Supreme Court Review_ Vol 2024.pdf",
            "TSCR",
            "Purdue Pharma Bankruptcy",
        ),
        (
            downloads
            / 'The Old Regime and the Loper Bright "Revolution"_ The Supreme Court Review_ Vol 2024.html',
            downloads
            / 'The Old Regime and the Loper Bright "Revolution"_ The Supreme Court Review_ Vol 2024.pdf',
            "TSCR",
            "Loper Bright Revolution",
        ),
        (
            downloads / "Fear of Balancing_ The Supreme Court Review_ Vol 2024.html",
            downloads / "Fear of Balancing_ The Supreme Court Review_ Vol 2024.pdf",
            "TSCR",
            "Fear of Balancing",
        ),
        (
            downloads
            / "The Trump Disqualification Case_ The Halley's Comet Of Constitutional Law_ The Supreme Court Review_ Vol 2024.html",
            downloads
            / "The Trump Disqualification Case_ The Halley's Comet Of Constitutional Law_ The Supreme Court Review_ Vol 2024.pdf",
            "TSCR",
            "Trump Disqualification",
        ),
        (
            downloads
            / "The Presidency After Trump v. United States_ The Supreme Court Review_ Vol 2024.html",
            downloads
            / "The Presidency After Trump v. United States_ The Supreme Court Review_ Vol 2024.pdf",
            "TSCR",
            "Presidency After Trump",
        ),
    ]

    # Additional Penn pairs
    penn_pairs = [
        (
            downloads
            / "Common-Law Limits on Firearms Purchases by Minors_ The Original Understanding - Penn Law Review.html",
            downloads / "Common-Law Limits on Firearms Purchases by Minors_ The Original U.pdf",
            "Penn",
            "Firearms Purchases by Minors",
        ),
        (
            downloads / "Against The Sliding Scale - Penn Law Review.html",
            downloads / "Against the Sliding Scale.pdf",
            "Penn",
            "Against the Sliding Scale",
        ),
    ]

    all_pairs = tscr_pairs + penn_pairs

    print(f"Found {len(tscr_pairs)} Supreme Court Review pairs")
    print(f"Found {len(penn_pairs)} additional Penn pairs")
    print(f"Total: {len(all_pairs)} pairs\n")

    results = []

    for html_file, pdf_file, source, title in all_pairs:
        if not html_file.exists():
            print(f"⚠️  HTML not found: {html_file.name}")
            continue
        if not pdf_file.exists():
            print(f"⚠️  PDF not found: {pdf_file.name}")
            continue

        print(f"\n{'=' * 70}")
        print(f"Testing: {source} - {title}")
        print(f"{'=' * 70}")
        print(f"  HTML: {html_file.name[:60]}...")
        print(f"  PDF:  {pdf_file.name[:60]}...")

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

    for source in ["TSCR", "Penn"]:
        source_results = [r for r in results if r["source"] == source]
        if not source_results:
            continue

        accepted = [r for r in source_results if r["status"] == "ACCEPT"]
        rejected = [r for r in source_results if r["status"] == "REJECT"]

        print(f"\n{source}:")
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
    validate_tscr_penn_pairs()
