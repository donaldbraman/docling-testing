#!/usr/bin/env python3
"""Diagnose Penn HTML vs PDF extraction to understand mismatch."""

import re
from pathlib import Path

from bs4 import BeautifulSoup
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import LayoutOptions, PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption


def normalize_text(text: str) -> str:
    """Normalize text for matching."""
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"-\s+", "", text)
    return text.strip()


def diagnose_pair():
    """Diagnose Penn Against the Sliding Scale extraction."""
    downloads = Path.home() / "Downloads"

    html_file = downloads / "Against The Sliding Scale - Penn Law Review.html"
    pdf_file = downloads / "Against the Sliding Scale.pdf"

    print("🔍 Diagnosing Penn 'Against the Sliding Scale' extraction\n")
    print("=" * 70)

    # Extract from HTML
    print("\n📄 HTML EXTRACTION")
    print("-" * 70)

    with open(html_file, encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    # Remove script and style
    for script in soup(["script", "style"]):
        script.decompose()

    # Get all text
    all_text = soup.get_text(separator="\n", strip=True)
    print(f"Total HTML text length: {len(all_text)} chars")
    print(f"Total HTML words: {len(all_text.split())}")

    # Extract paragraphs
    html_paras = []
    for p in soup.find_all("p"):
        text = normalize_text(p.get_text())
        if len(text) > 20:
            html_paras.append(text)

    print(f"Paragraphs from <p> tags (>20 chars): {len(html_paras)}")

    # Show first 5 paragraphs
    print("\nFirst 5 HTML paragraphs:")
    for i, para in enumerate(html_paras[:5], 1):
        print(f"{i}. ({len(para)} chars) {para[:100]}...")

    # Check for article/content sections
    article = soup.find("article")
    if article:
        print("\n✓ Found <article> tag")
        article_text = article.get_text(separator=" ", strip=True)
        print(f"  Article text: {len(article_text.split())} words")

    # Check for main content
    main = soup.find("main")
    if main:
        print("✓ Found <main> tag")
        main_text = main.get_text(separator=" ", strip=True)
        print(f"  Main text: {len(main_text.split())} words")

    # Extract from PDF
    print("\n\n📄 PDF EXTRACTION")
    print("-" * 70)

    pipeline = PdfPipelineOptions(
        layout_options=LayoutOptions(),
        generate_parsed_pages=True,
        generate_page_images=True,
        images_scale=1.0,
    )

    converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline)}
    )

    result = converter.convert(str(pdf_file))

    pdf_paras = []
    for item, _level in result.document.iterate_items():
        if hasattr(item, "text") and item.text:
            text = normalize_text(item.text)
            if len(text) > 20:
                pdf_paras.append(text)

    print(f"PDF paragraphs (>20 chars): {len(pdf_paras)}")

    all_pdf_text = " ".join(pdf_paras)
    print(f"Total PDF words: {len(all_pdf_text.split())}")

    # Show first 5 paragraphs
    print("\nFirst 5 PDF paragraphs:")
    for i, para in enumerate(pdf_paras[:5], 1):
        print(f"{i}. ({len(para)} chars) {para[:100]}...")

    # Comparison
    print("\n\n📊 COMPARISON")
    print("=" * 70)
    print(f"HTML paragraphs: {len(html_paras)}")
    print(f"PDF paragraphs:  {len(pdf_paras)}")
    print(f"Ratio: {len(pdf_paras) / len(html_paras):.1f}x more in PDF")

    # Check for common content
    print("\n🔍 Content overlap check:")

    # Sample some text from beginning of both
    html_start = " ".join(html_paras[:3])
    pdf_start = " ".join(pdf_paras[:3])

    html_words = set(html_start.lower().split())
    pdf_words = set(pdf_start.lower().split())

    common = html_words & pdf_words
    print(f"First 3 paragraphs - common words: {len(common)}/{len(html_words)} HTML words")

    # Check if HTML might be abstract/preview
    if len(html_paras) < len(pdf_paras) * 0.5:
        print("\n⚠️  WARNING: HTML has <50% of PDF paragraphs")
        print("   This suggests HTML may be abstract/preview only")

    # Check for "abstract" or "preview" indicators in HTML
    html_lower = all_text.lower()
    if "abstract" in html_lower[:1000]:
        print("\n⚠️  'Abstract' found in first 1000 chars of HTML")

    # Check HTML structure for common paywalled patterns
    print("\n🔍 Checking for paywall indicators:")
    if soup.find(string=re.compile(r"(subscribe|sign in|log in|access)", re.I)):
        print("   ⚠️  Found potential paywall text")

    # Look for truncation indicators
    if soup.find(string=re.compile(r"(read more|continue reading|full text)", re.I)):
        print("   ⚠️  Found 'read more' / 'continue reading' text")


if __name__ == "__main__":
    diagnose_pair()
