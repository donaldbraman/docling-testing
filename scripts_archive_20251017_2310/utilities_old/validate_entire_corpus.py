#!/usr/bin/env python3
"""Validate entire corpus using training pipeline's paragraph matching method."""

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
    try:
        with open(html_path, encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "html.parser")
    except Exception as e:
        print(f"  ⚠️  Error reading HTML: {e}")
        return []

    # Remove script and style
    for script in soup(["script", "style"]):
        script.decompose()

    paragraphs = []
    for p in soup.find_all("p"):
        text = normalize_text(p.get_text())
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

    try:
        result = converter.convert(str(pdf_path))
    except Exception as e:
        print(f"  ⚠️  Error converting PDF: {e}")
        return []

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
    """
    matched_count = 0
    total_similarity = 0.0

    for pdf_text in pdf_paras:
        best_score = 0.0

        # Find best matching HTML paragraph
        for html_text in html_paras:
            score = SequenceMatcher(None, pdf_text, html_text).ratio()
            if score > best_score:
                best_score = score

        # Count as match if ≥ threshold
        if best_score >= threshold:
            matched_count += 1
            total_similarity += best_score

    avg_similarity = (total_similarity / matched_count) if matched_count > 0 else 0.0

    return matched_count, len(pdf_paras), avg_similarity


def validate_corpus():
    """Validate all pairs in data/raw_html and data/raw_pdf."""
    html_dir = Path("data/raw_html")
    pdf_dir = Path("data/raw_pdf")

    if not html_dir.exists() or not pdf_dir.exists():
        print("❌ Corpus directories not found: data/raw_html/ or data/raw_pdf/")
        return

    # Find all HTML files
    html_files = sorted(html_dir.glob("*.html"))

    print("🔍 Validating entire corpus with SequenceMatcher (training pipeline method)")
    print(f"Found {len(html_files)} HTML files in corpus\n")
    print("=" * 70)

    results = []
    errors = []

    for html_file in html_files:
        # Find corresponding PDF
        pdf_file = pdf_dir / html_file.with_suffix(".pdf").name

        if not pdf_file.exists():
            errors.append(f"Missing PDF for: {html_file.name}")
            continue

        basename = html_file.stem
        print(f"\n{basename}")
        print("-" * 70)

        # Extract paragraphs
        print("  Extracting HTML...")
        html_paras = extract_paragraphs_from_html(html_file)
        if not html_paras:
            errors.append(f"No HTML paragraphs: {basename}")
            continue
        print(f"    {len(html_paras)} paragraphs")

        print("  Extracting PDF...")
        pdf_paras = extract_paragraphs_from_pdf(pdf_file)
        if not pdf_paras:
            errors.append(f"No PDF paragraphs: {basename}")
            continue
        print(f"    {len(pdf_paras)} paragraphs")

        # Match paragraphs
        print("  Matching...")
        matched, total, avg_sim = match_paragraphs(html_paras, pdf_paras)
        match_rate = (matched / total * 100) if total > 0 else 0

        print(f"  Results: {matched}/{total} matched ({match_rate:.1f}%), avg {avg_sim:.1%}")

        status = "✅ PASS" if match_rate >= 75 else "❌ FAIL"
        print(f"  Status: {status}")

        results.append(
            {
                "basename": basename,
                "matched": matched,
                "total": total,
                "match_rate": match_rate,
                "avg_similarity": avg_sim,
                "status": "PASS" if match_rate >= 75 else "FAIL",
            }
        )

    # Summary
    print(f"\n\n{'=' * 70}")
    print("CORPUS VALIDATION SUMMARY")
    print(f"{'=' * 70}\n")

    passed = [r for r in results if r["status"] == "PASS"]
    failed = [r for r in results if r["status"] == "FAIL"]

    print(f"✅ PASSED (≥75% match rate): {len(passed)}")
    for r in sorted(passed, key=lambda x: x["match_rate"], reverse=True):
        print(f"   {r['match_rate']:5.1f}% ({r['matched']:3d}/{r['total']:3d}) - {r['basename']}")

    if failed:
        print(f"\n❌ FAILED (<75% match rate): {len(failed)}")
        for r in sorted(failed, key=lambda x: x["match_rate"]):
            print(
                f"   {r['match_rate']:5.1f}% ({r['matched']:3d}/{r['total']:3d}) - {r['basename']}"
            )

    if errors:
        print(f"\n⚠️  ERRORS: {len(errors)}")
        for error in errors:
            print(f"   {error}")

    if passed:
        avg_match_rate = sum(r["match_rate"] for r in passed) / len(passed)
        avg_similarity = sum(r["avg_similarity"] for r in passed) / len(passed)
        print("\n📊 Passed pairs average:")
        print(f"   Match rate: {avg_match_rate:.1f}%")
        print(f"   Similarity: {avg_similarity:.1%}")

    print(f"\n{'=' * 70}")
    print(f"OVERALL: {len(passed)}/{len(results)} pairs passed validation")

    if failed:
        print(f"\n⚠️  RECOMMENDATION: Remove {len(failed)} failed pairs before training")
        print("   Failed pairs should be moved to a quarantine folder or deleted")

    return results


if __name__ == "__main__":
    validate_corpus()
