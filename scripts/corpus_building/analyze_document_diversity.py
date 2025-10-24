#!/usr/bin/env python3
"""
Analyze structural diversity of documents to optimize training data selection.

Looks for:
- Documents with running footers (page numbers at bottom)
- Documents with no/minimal front matter (< 3 pages)
- Documents with different length profiles (short, medium, long)
- Documents with different footnote densities

Usage:
    uv run python scripts/corpus_building/analyze_document_diversity.py
"""

import json
from pathlib import Path

import fitz  # PyMuPDF


def analyze_document_structure(pdf_path: Path, gt_path: Path) -> dict:
    """Analyze structural characteristics of a document."""

    # Load ground truth
    with open(gt_path) as f:
        gt = json.load(f)

    body_count = len(gt.get("body_text_paragraphs", []))
    footnote_count = len(gt.get("footnotes", []))

    # Open PDF
    doc = fitz.open(pdf_path)
    page_count = len(doc)

    # Check for footers (page numbers at bottom of pages)
    has_footer = False
    footer_pages = 0

    for page_num in range(min(5, page_count)):  # Check first 5 pages
        page = doc[page_num]
        page_dict = page.get_text("dict")
        page_height = page.rect.height

        # Look for text at bottom of page
        for block in page_dict["blocks"]:
            if "lines" not in block:
                continue

            bbox = block["bbox"]
            y_position = bbox[1] / page_height

            # Bottom 10% of page
            if y_position > 0.9:
                # Check if it looks like a page number
                text = ""
                for line in block["lines"]:
                    for span in line["spans"]:
                        text += span["text"]

                # Simple heuristic: contains digits, short, at bottom
                if any(c.isdigit() for c in text) and len(text) < 50:
                    has_footer = True
                    footer_pages += 1
                    break

    doc.close()

    # Estimate front matter length (pages before body text starts)
    # Assume body text starts on page where we have significant content
    front_matter_pages = 1  # Minimum
    if page_count > 10:
        # Heuristic: front matter is typically 2-5 pages in law reviews
        if body_count > 100:  # Long article
            front_matter_pages = 3
        elif body_count > 50:  # Medium article
            front_matter_pages = 2

    # Calculate metrics
    footnote_density = footnote_count / body_count if body_count > 0 else 0

    return {
        "name": pdf_path.stem,
        "pages": page_count,
        "body_paragraphs": body_count,
        "footnotes": footnote_count,
        "footnote_density": round(footnote_density, 2),
        "has_footer": has_footer,
        "footer_page_count": footer_pages,
        "estimated_front_matter_pages": front_matter_pages,
        "length_category": (
            "short" if page_count < 25 else "medium" if page_count < 50 else "long"
        ),
    }


def main():
    pdf_dir = Path("data/v3_data/raw_pdf")
    gt_dir = Path("results/ocr_pipeline_evaluation/ground_truth")

    documents = []

    print("Analyzing document structural diversity...")
    print("=" * 80)

    for pdf_path in sorted(pdf_dir.glob("*.pdf")):
        gt_path = gt_dir / f"{pdf_path.stem}_ground_truth.json"

        if not gt_path.exists():
            continue

        try:
            doc_info = analyze_document_structure(pdf_path, gt_path)
            documents.append(doc_info)
        except Exception as e:
            print(f"Error analyzing {pdf_path.stem}: {e}")

    print(f"\nAnalyzed {len(documents)} documents\n")

    # Find diverse examples
    print("=" * 80)
    print("DOCUMENTS WITH RUNNING FOOTERS")
    print("=" * 80)
    with_footers = [d for d in documents if d["has_footer"]]
    print(f"\nFound {len(with_footers)} documents with footers")
    for doc in sorted(with_footers, key=lambda x: -x["footer_page_count"])[:10]:
        print(
            f"  {doc['name'][:60]:<60} {doc['pages']:3d}p, "
            f"{doc['footer_page_count']} pages with footer"
        )

    print("\n" + "=" * 80)
    print("SHORT DOCUMENTS (< 25 pages, minimal front matter)")
    print("=" * 80)
    short_docs = [
        d for d in documents if d["length_category"] == "short" and d["body_paragraphs"] > 20
    ]
    print(f"\nFound {len(short_docs)} short documents with substantial content")
    for doc in sorted(short_docs, key=lambda x: x["pages"])[:10]:
        print(f"  {doc['name'][:60]:<60} {doc['pages']:3d}p, {doc['body_paragraphs']:3d} body ¶")

    print("\n" + "=" * 80)
    print("HIGH FOOTNOTE DENSITY (> 1.5 footnotes per paragraph)")
    print("=" * 80)
    high_footnote = [d for d in documents if d["footnote_density"] > 1.5]
    print(f"\nFound {len(high_footnote)} documents with high footnote density")
    for doc in sorted(high_footnote, key=lambda x: -x["footnote_density"])[:10]:
        print(
            f"  {doc['name'][:60]:<60} density: {doc['footnote_density']:.2f}, "
            f"{doc['footnotes']} footnotes"
        )

    print("\n" + "=" * 80)
    print("MINIMAL/NO FOOTNOTES (< 10 footnotes)")
    print("=" * 80)
    low_footnote = [d for d in documents if d["footnotes"] < 10 and d["body_paragraphs"] > 50]
    print(f"\nFound {len(low_footnote)} documents with minimal footnotes")
    for doc in sorted(low_footnote, key=lambda x: x["footnotes"])[:10]:
        print(
            f"  {doc['name'][:60]:<60} {doc['footnotes']:3d} footnotes, "
            f"{doc['body_paragraphs']:3d} body ¶"
        )

    # Recommend diverse training set
    print("\n" + "=" * 80)
    print("RECOMMENDED DIVERSE TRAINING SET (Documents 3-7)")
    print("=" * 80)

    recommendations = []

    # Doc 3: With footer
    if with_footers:
        rec = with_footers[0]
        rec["reason"] = "Has running footer (missing from doc 1)"
        recommendations.append(rec)

    # Doc 4: Short document
    if short_docs:
        rec = [d for d in short_docs if d not in recommendations][0]
        rec["reason"] = "Short with minimal front matter"
        recommendations.append(rec)

    # Doc 5: High footnote density
    if high_footnote:
        rec = [d for d in high_footnote if d not in recommendations][0]
        rec["reason"] = "High footnote density"
        recommendations.append(rec)

    # Doc 6: Minimal footnotes
    if low_footnote:
        rec = [d for d in low_footnote if d not in recommendations][0]
        rec["reason"] = "Minimal footnotes (different pattern)"
        recommendations.append(rec)

    # Doc 7: Long document
    long_docs = [d for d in documents if d["length_category"] == "long"]
    if long_docs:
        rec = [d for d in long_docs if d not in recommendations][0]
        rec["reason"] = "Long document (> 50 pages)"
        recommendations.append(rec)

    print("\nDoc#  Name                                                        Pages  Reason")
    print("-" * 80)
    for i, doc in enumerate(recommendations, 3):
        print(f"  {i}   {doc['name'][:55]:<55} {doc['pages']:3d}p  {doc['reason']}")

    print("\nThis diverse set will train the model to handle:")
    print("  ✓ Footers (doc 1 had 0 footer examples)")
    print("  ✓ Short documents with minimal front matter")
    print("  ✓ Variable footnote densities")
    print("  ✓ Different document lengths")


if __name__ == "__main__":
    main()
