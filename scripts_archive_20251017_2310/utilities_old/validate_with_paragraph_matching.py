#!/usr/bin/env python3
"""Validate pairs using actual training pipeline paragraph matching (SequenceMatcher)."""

import re
from difflib import SequenceMatcher
from pathlib import Path

from bs4 import BeautifulSoup
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import LayoutOptions, PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption


def normalize_text(text: str) -> str:
    """Normalize text for matching (same as training pipeline)."""
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"-\s+", "", text)
    return text.strip()


def extract_paragraphs_from_html(html_path: Path) -> list[str]:
    """Extract paragraphs from HTML."""
    with open(html_path, encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    # Remove script and style
    for script in soup(["script", "style"]):
        script.decompose()

    paragraphs = []
    for p in soup.find_all("p"):
        text = p.get_text()
        text = normalize_text(text)
        if len(text) > 20:
            paragraphs.append(text)

    return paragraphs


def extract_paragraphs_from_pdf(pdf_path: Path) -> list[str]:
    """Extract paragraphs from PDF using training pipeline settings."""
    # Use training pipeline configuration (LayoutOptions, no OCR)
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
            text = normalize_text(item.text)
            if len(text) > 20:
                paragraphs.append(text)

    return paragraphs


def match_paragraphs(html_paras: list[str], pdf_paras: list[str], threshold: float = 0.75):
    """
    Match PDF paragraphs to HTML using SequenceMatcher (same as training pipeline).

    Returns:
        matched: Number of PDF paragraphs matched
        total: Total PDF paragraphs
        avg_similarity: Average similarity of matches
        match_details: List of (pdf_idx, html_idx, similarity) tuples
    """
    matched_count = 0
    total_similarity = 0.0
    match_details = []

    for pdf_idx, pdf_text in enumerate(pdf_paras):
        best_match_idx = None
        best_score = 0.0

        # Find best matching HTML paragraph
        for html_idx, html_text in enumerate(html_paras):
            score = SequenceMatcher(None, pdf_text, html_text).ratio()

            if score > best_score:
                best_score = score
                best_match_idx = html_idx

        # Count as match if ≥ threshold
        if best_score >= threshold:
            matched_count += 1
            total_similarity += best_score
            match_details.append((pdf_idx, best_match_idx, best_score))

    avg_similarity = (total_similarity / matched_count) if matched_count > 0 else 0.0

    return matched_count, len(pdf_paras), avg_similarity, match_details


def validate_jels_pairs():
    """Validate JELS pairs using paragraph matching."""
    downloads = Path.home() / "Downloads"

    jels_pairs = [
        (
            downloads
            / "Hiding Lawyer Misconduct_ Evidence From Florida - Rozema - 2025 - Journal of Empirical Legal Studies - Wiley Online Library.html",
            downloads
            / "J Empirical Legal Studies - 2025 - Rozema - Hiding Lawyer Misconduct  Evidence From Florida.pdf",
            "Hiding Lawyer Misconduct",
        ),
        (
            downloads
            / "In the Eye of the Beholder_ How Lawyers Perceive Legal Ethical Problems - Yoon - 2025 - Journal of Empirical Legal Studies - Wiley Online Library.html",
            downloads
            / "J Empirical Legal Studies - 2025 - Yoon - In the Eye of the Beholder  How Lawyers Perceive Legal Ethical Problems.pdf",
            "In the Eye of the Beholder",
        ),
        (
            downloads
            / "Transnational Litigation in U.S. Courts_ A Theoretical and Empirical Reassessment - Whytock - 2022 - Journal of Empirical Legal Studies - Wiley Online Library.html",
            downloads
            / "J Empirical Legal Studies - 2022 - Whytock - Transnational Litigation in U S  Courts  A Theoretical and Empirical.pdf",
            "Transnational Litigation",
        ),
        (
            downloads
            / "The Diffusion of Deal Innovations in Complex Contractual Networks - Bishop - 2025 - Journal of Empirical Legal Studies - Wiley Online Library.html",
            downloads
            / "J Empirical Legal Studies - 2025 - Bishop - The Diffusion of Deal Innovations in Complex Contractual Networks.pdf",
            "Deal Innovations",
        ),
        (
            downloads
            / "Measuring the Perceived (In)accessibility of Courts and Lawyers - Denvir - 2025 - Journal of Empirical Legal Studies - Wiley Online Library.html",
            downloads
            / "J Empirical Legal Studies - 2025 - Denvir - Measuring the Perceived  In accessibility of Courts and Lawyers.pdf",
            "Courts Accessibility",
        ),
    ]

    print("🔍 Validating JELS pairs with SequenceMatcher (training pipeline method)\n")
    print(f"Found {len(jels_pairs)} JELS pairs\n")

    results = []

    for html_file, pdf_file, title in jels_pairs:
        if not html_file.exists() or not pdf_file.exists():
            print(f"⚠️  Files not found for: {title}")
            continue

        print(f"\n{'=' * 70}")
        print(f"Testing: {title}")
        print(f"{'=' * 70}")

        # Extract paragraphs
        print("  Extracting from HTML...")
        html_paras = extract_paragraphs_from_html(html_file)
        print(f"    Found {len(html_paras)} paragraphs")

        print("  Extracting from PDF (LayoutOptions)...")
        pdf_paras = extract_paragraphs_from_pdf(pdf_file)
        print(f"    Found {len(pdf_paras)} paragraphs")

        # Match paragraphs
        print("  Matching paragraphs...")
        matched, total, avg_sim, details = match_paragraphs(html_paras, pdf_paras)

        match_rate = (matched / total * 100) if total > 0 else 0

        print("\n  Results:")
        print(f"    Matched:     {matched}/{total} ({match_rate:.1f}%)")
        print(f"    Avg similarity: {avg_sim:.1%}")

        # Show sample matches
        if details:
            print("\n  Sample matches (first 3):")
            for pdf_idx, html_idx, sim in details[:3]:
                print(f"    PDF[{pdf_idx}] → HTML[{html_idx}]: {sim:.1%}")
                print(f"      PDF:  {pdf_paras[pdf_idx][:80]}...")
                print(f"      HTML: {html_paras[html_idx][:80]}...")

        status = "✅ ACCEPT" if match_rate >= 75 else "❌ REJECT"
        print(f"\n    Status: {status}")

        results.append(
            {
                "title": title,
                "matched": matched,
                "total": total,
                "match_rate": match_rate,
                "avg_similarity": avg_sim,
                "status": "ACCEPT" if match_rate >= 75 else "REJECT",
            }
        )

    # Summary
    print(f"\n\n{'=' * 70}")
    print("VALIDATION SUMMARY")
    print(f"{'=' * 70}\n")

    accepted = [r for r in results if r["status"] == "ACCEPT"]
    rejected = [r for r in results if r["status"] == "REJECT"]

    print(f"✅ Accepted (≥75% match rate): {len(accepted)}")
    for r in accepted:
        print(f"   {r['match_rate']:5.1f}% ({r['matched']}/{r['total']}) - {r['title']}")

    if rejected:
        print(f"\n❌ Rejected (<75% match rate): {len(rejected)}")
        for r in rejected:
            print(f"   {r['match_rate']:5.1f}% ({r['matched']}/{r['total']}) - {r['title']}")

    if accepted:
        avg_match_rate = sum(r["match_rate"] for r in accepted) / len(accepted)
        avg_similarity = sum(r["avg_similarity"] for r in accepted) / len(accepted)
        print("\n📊 Accepted pairs average:")
        print(f"   Match rate: {avg_match_rate:.1f}%")
        print(f"   Similarity: {avg_similarity:.1%}")

    print(f"\n{'=' * 70}")
    print(f"OVERALL: {len(accepted)}/{len(results)} pairs passed validation")

    return results


if __name__ == "__main__":
    validate_jels_pairs()
