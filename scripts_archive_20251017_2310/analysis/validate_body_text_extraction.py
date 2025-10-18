#!/usr/bin/env python3
"""Compare Docling's body text extraction vs HTML ground truth."""

import json
from difflib import SequenceMatcher
from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption


def normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    # Remove extra whitespace, normalize line breaks
    text = " ".join(text.split())
    return text.lower().strip()


def compare_body_text(pdf_path: Path, html_path: Path):
    """Compare body text extraction from PDF vs HTML."""

    basename = pdf_path.stem

    print(f"\n{'=' * 80}")
    print(f"VALIDATING: {basename}")
    print(f"{'=' * 80}\n")

    # Extract from PDF with Docling
    print("📄 Extracting from PDF with Docling...")
    converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=PdfPipelineOptions())}
    )
    result = converter.convert(str(pdf_path))

    # Get Docling's body text (labeled as "text")
    docling_body = []
    docling_footnotes = []
    for item, _level in result.document.iterate_items():
        if hasattr(item, "text") and item.text:
            label = str(item.label) if hasattr(item, "label") else "unknown"
            if label == "text":
                docling_body.append(normalize_text(item.text))
            elif label == "footnote":
                docling_footnotes.append(normalize_text(item.text))

    # Load HTML ground truth
    print("🌐 Loading HTML ground truth...")
    if not html_path.exists():
        print(f"❌ HTML file not found: {html_path}")
        return

    with open(html_path) as f:
        html_data = json.load(f)

    html_body = []
    html_footnotes = []
    for p in html_data["paragraphs"]:
        text = normalize_text(p["text"])
        if p["label"] == "body-text":
            html_body.append(text)
        elif p["label"] == "footnote-text":
            html_footnotes.append(text)

    # Compare counts
    print(f"\n{'=' * 80}")
    print("LABEL COUNTS")
    print(f"{'=' * 80}")
    print(f"Docling body text blocks:     {len(docling_body):>4}")
    print(f"HTML body text blocks:        {len(html_body):>4}")
    print(f"Docling footnote blocks:      {len(docling_footnotes):>4}")
    print(f"HTML footnote blocks:         {len(html_footnotes):>4}")

    # Calculate text similarity for body text
    docling_body_combined = " ".join(docling_body)
    html_body_combined = " ".join(html_body)

    matcher = SequenceMatcher(None, docling_body_combined, html_body_combined)
    similarity = matcher.ratio() * 100

    print(f"\n{'=' * 80}")
    print("BODY TEXT SIMILARITY")
    print(f"{'=' * 80}")
    print(f"Text similarity: {similarity:.1f}%")

    # Identify errors
    errors = []

    # Check if Docling is missing body text
    if len(docling_body) < len(html_body) * 0.8:
        missing_pct = ((len(html_body) - len(docling_body)) / len(html_body)) * 100
        errors.append(f"⚠️  Docling missing {missing_pct:.1f}% of body text blocks")

    # Check if Docling is over-extracting body text
    if len(docling_body) > len(html_body) * 1.2:
        extra_pct = ((len(docling_body) - len(html_body)) / len(html_body)) * 100
        errors.append(f"⚠️  Docling extracting {extra_pct:.1f}% MORE body text than expected")

    # Check if similarity is too low
    if similarity < 90:
        errors.append(f"⚠️  Body text similarity is only {similarity:.1f}% (expected >90%)")

    # Check if Docling labeled body text as footnotes
    if len(docling_footnotes) > len(html_footnotes) * 1.5:
        errors.append(
            f"⚠️  Docling found {len(docling_footnotes)} footnotes but HTML has {len(html_footnotes)}"
        )

    # Report results
    print(f"\n{'=' * 80}")
    print("VALIDATION RESULTS")
    print(f"{'=' * 80}")

    if not errors:
        print("✅ PASS: Body text extraction is accurate")
    else:
        print("❌ FAIL: Body text extraction has errors:")
        for error in errors:
            print(f"   {error}")

    return {
        "basename": basename,
        "docling_body_count": len(docling_body),
        "html_body_count": len(html_body),
        "similarity": similarity,
        "passed": len(errors) == 0,
        "errors": errors,
    }


def main():
    """Validate body text extraction for one article from each journal."""

    # Map of journals to sample HTML-PDF pairs
    # We'll test one from each journal that has HTML ground truth
    test_pairs = [
        (
            "BU Law Review",
            "data/raw_pdf/bu_law_review_online_fourth_amendment_secure.pdf",
            "data/labeled_html_v2/bu_law_review_online_fourth_amendment_secure.json",
        ),
        # Add more when we have labeled HTML for other journals
    ]

    results = []
    for journal, pdf_rel, html_rel in test_pairs:
        pdf_path = Path(pdf_rel)
        html_path = Path(html_rel)

        if pdf_path.exists() and html_path.exists():
            print(f"\n\n{'#' * 80}")
            print(f"# JOURNAL: {journal}")
            print(f"{'#' * 80}")

            result = compare_body_text(pdf_path, html_path)
            if result:
                result["journal"] = journal
                results.append(result)
        else:
            print(f"⚠️  Skipping {journal} - files not found")

    # Summary report
    print(f"\n\n{'=' * 80}")
    print("SUMMARY: BODY TEXT EXTRACTION VALIDATION")
    print(f"{'=' * 80}\n")

    if results:
        passed = sum(1 for r in results if r["passed"])
        total = len(results)

        print(f"Journals tested: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print()

        for result in results:
            status = "✅ PASS" if result["passed"] else "❌ FAIL"
            print(f"{result['journal']:40} {status} ({result['similarity']:.1f}% similarity)")

        if passed < total:
            print(f"\n{'=' * 80}")
            print("RECOMMENDATION")
            print(f"{'=' * 80}")
            print("Docling has body text extraction errors.")
            print("We should train ModernBERT to correct these errors using HTML as ground truth.")
    else:
        print("No test pairs found.")


if __name__ == "__main__":
    main()
