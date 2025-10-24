#!/usr/bin/env python3
"""
Generate color overlay PDFs showing Tesseract vs ocrmac extraction results.

Creates overlays for comparison:
- Red: Text only found by ocrmac (baseline)
- Blue: Text only found by Tesseract
- Green: Text found by both
"""

import json
import re
from pathlib import Path

import fitz  # PyMuPDF


def normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    return re.sub(r"\s+", " ", text).strip().lower()


def create_overlay_pdf(
    original_pdf: Path, tesseract_extraction: Path, baseline_extraction: Path, output_path: Path
) -> None:
    """Create overlay PDF showing extraction comparison."""

    print(f"\nProcessing: {original_pdf.name}")

    # Load extractions
    with open(tesseract_extraction) as f:
        tess_data = json.load(f)
    with open(baseline_extraction) as f:
        base_data = json.load(f)

    tess_texts = {normalize_text(t) for t in tess_data.get("texts", []) if t.strip()}
    base_texts = {normalize_text(t) for t in base_data.get("texts", []) if t.strip()}

    # Find unique and shared text
    only_tesseract = tess_texts - base_texts
    only_baseline = base_texts - tess_texts
    both = tess_texts & base_texts

    print("  Text blocks:")
    print(f"    Both engines: {len(both)}")
    print(f"    Only Tesseract: {len(only_tesseract)}")
    print(f"    Only ocrmac: {len(only_baseline)}")

    # Open PDF
    doc = fitz.open(str(original_pdf))

    # Search for text and overlay rectangles
    total_rects = 0

    for page_num in range(len(doc)):
        page = doc[page_num]

        # Overlay text found by both (green)
        for text in both:
            if len(text) < 5:  # Skip very short strings
                continue
            areas = page.search_for(text)
            for rect in areas:
                page.draw_rect(rect, color=(0, 1, 0), width=0.5, fill=(0, 1, 0), fill_opacity=0.1)
                total_rects += 1

        # Overlay text only in Tesseract (blue)
        for text in only_tesseract:
            if len(text) < 5:
                continue
            areas = page.search_for(text)
            for rect in areas:
                page.draw_rect(rect, color=(0, 0, 1), width=0.5, fill=(0, 0, 1), fill_opacity=0.15)
                total_rects += 1

        # Overlay text only in baseline (red)
        for text in only_baseline:
            if len(text) < 5:
                continue
            areas = page.search_for(text)
            for rect in areas:
                page.draw_rect(rect, color=(1, 0, 0), width=0.5, fill=(1, 0, 0), fill_opacity=0.15)
                total_rects += 1

    # Save overlay PDF
    doc.save(str(output_path))
    doc.close()

    print(f"  ✓ Created overlay with {total_rects} highlighted regions")
    print(f"  Saved: {output_path.name}")


def main():
    """Generate overlays for worst-performing PDFs."""

    # Directories
    pdf_dir = Path("data/v3_data/raw_pdf")
    tesseract_dir = Path("results/tesseract_corpus_pipeline/tesseract_extractions")
    baseline_dir = Path("results/ocr_pipeline_evaluation/extractions")
    comparison_dir = Path("results/tesseract_corpus_pipeline/comparisons")
    overlay_dir = Path("results/tesseract_corpus_pipeline/overlays")

    overlay_dir.mkdir(parents=True, exist_ok=True)

    # Get all comparisons sorted by coverage (worst first)
    comparison_files = sorted(comparison_dir.glob("*.json"))
    comparisons = []

    for comp_file in comparison_files:
        with open(comp_file) as f:
            data = json.load(f)
        comparisons.append(
            {
                "pdf_name": data["pdf_name"],
                "coverage": data["metrics"]["coverage_pct"],
                "comparison_file": comp_file,
            }
        )

    # Sort by coverage (worst first)
    comparisons.sort(key=lambda x: x["coverage"])

    print("=" * 80)
    print("GENERATING OVERLAY PDFs - Worst performers first")
    print("=" * 80)
    print("\nLegend:")
    print("  🟢 Green:  Text found by BOTH engines")
    print("  🔵 Blue:   Text ONLY found by Tesseract")
    print("  🔴 Red:    Text ONLY found by ocrmac")
    print("=" * 80)

    # Generate overlays for worst 5 performers
    for i, comp in enumerate(comparisons[:5], 1):
        pdf_name = comp["pdf_name"]
        coverage = comp["coverage"]

        print(f"\n[{i}/5] {pdf_name} (coverage: {coverage:.1f}%)")

        # Paths
        original_pdf = pdf_dir / f"{pdf_name}.pdf"
        tesseract_extraction = tesseract_dir / f"{pdf_name}_tesseract_extraction.json"
        baseline_extraction = baseline_dir / f"{pdf_name}_baseline_extraction.json"
        output_path = overlay_dir / f"{pdf_name}_overlay.pdf"

        if not original_pdf.exists():
            print(f"  ⚠️  Original PDF not found: {original_pdf.name}")
            continue

        if not tesseract_extraction.exists():
            print("  ⚠️  Tesseract extraction not found")
            continue

        if not baseline_extraction.exists():
            print("  ⚠️  Baseline extraction not found")
            continue

        try:
            create_overlay_pdf(original_pdf, tesseract_extraction, baseline_extraction, output_path)
        except Exception as e:
            print(f"  ✗ Failed: {e}")

    print("\n" + "=" * 80)
    print("OVERLAY GENERATION COMPLETE")
    print("=" * 80)
    print(f"Overlays saved to: {overlay_dir}")
    print("\nTo view:")
    print(f"  open {overlay_dir}")


if __name__ == "__main__":
    main()
