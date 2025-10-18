#!/usr/bin/env python3
"""Export CSV comparing Docling labels vs ground truth labels."""

import csv
import json
import re
from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import LayoutOptions, PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from rapidfuzz import fuzz

LABELED_HTML_DIR = Path("data/labeled_html")
PDF_DIR = Path("data/raw_pdf")
CACHE_DIR = Path("data/extraction_cache")
OUTPUT_DIR = Path("data/label_comparison_csv")


def normalize_text(text: str) -> str:
    """Normalize text for matching."""
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"-\s+", "", text)
    text = re.sub(r'["' '"]', '"', text)
    text = re.sub(r"[–—]", "-", text)
    return text.strip()


def get_cache_path(pdf_path: Path) -> Path:
    """Get cache path for Docling labels."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{pdf_path.stem}_docling_labels.json"


def is_cache_valid(cache_path: Path, source_path: Path) -> bool:
    """Check if cache is newer than source."""
    if not cache_path.exists():
        return False
    return cache_path.stat().st_mtime > source_path.stat().st_mtime


def extract_docling_labels(pdf_path: Path) -> list[dict]:
    """Extract Docling's labels for all items (with caching)."""
    cache_path = get_cache_path(pdf_path)

    # Try cache first
    if is_cache_valid(cache_path, pdf_path):
        try:
            with open(cache_path, encoding="utf-8") as f:
                print("  (loaded from cache)")
                return json.load(f)
        except Exception:
            pass

    pipeline = PdfPipelineOptions(
        layout_options=LayoutOptions(),
        generate_parsed_pages=True,
        generate_page_images=False,
    )

    converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline)}
    )

    try:
        result = converter.convert(str(pdf_path))
    except Exception as e:
        print(f"  ⚠️  Error converting PDF: {e}")
        return []

    # Extract all items with their labels
    items = []
    for item, _level in result.document.iterate_items():
        if hasattr(item, "text") and item.text:
            text = normalize_text(item.text)
            if len(text) > 20:  # Min length
                items.append(
                    {
                        "text": text,
                        "label": item.label.value if hasattr(item, "label") else "unknown",
                        "layer": item.layer.value if hasattr(item, "layer") else "unknown",
                    }
                )

    # Save to cache
    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"  ⚠️  Failed to save cache: {e}")

    return items


def load_ground_truth_labels(basename: str) -> list[dict]:
    """Load our ground truth labels from labeled HTML."""
    labeled_file = LABELED_HTML_DIR / f"{basename}.json"

    if not labeled_file.exists():
        return []

    try:
        with open(labeled_file, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"  ⚠️  Error loading labeled HTML: {e}")
        return []

    paragraphs = data.get("paragraphs", [])
    return [
        {
            "text": normalize_text(p["text"]),
            "label": p["label"],
        }
        for p in paragraphs
    ]


def fuzzy_match_texts(text1: str, text2: str, threshold: float = 0.85) -> tuple[bool, float]:
    """Check if two texts are similar enough to be the same."""
    # Exact match
    if text1 == text2:
        return True, 1.0

    # Fuzzy match
    score = fuzz.ratio(text1, text2) / 100.0
    return score >= threshold, score


def match_items(docling_items: list[dict], ground_truth_items: list[dict]) -> list[dict]:
    """Match Docling items to ground truth items."""
    matches = []

    for doc_item in docling_items:
        best_match = None
        best_score = 0

        for gt_item in ground_truth_items:
            matched, score = fuzzy_match_texts(doc_item["text"], gt_item["text"], threshold=0.85)
            if matched and score > best_score:
                best_score = score
                best_match = gt_item

        if best_match:
            matches.append(
                {
                    "pdf_text": doc_item["text"],
                    "html_text": best_match["text"],
                    "docling_label": doc_item["label"],
                    "docling_layer": doc_item["layer"],
                    "ground_truth_label": best_match["label"],
                    "match_score": best_score,
                }
            )

    return matches


def export_csv(basename: str, matches: list[dict]):
    """Export matches to CSV file."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = OUTPUT_DIR / f"{basename}.csv"

    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "pdf_text",
                "html_text",
                "docling_label",
                "docling_layer",
                "ground_truth_label",
                "match_score",
                "label_match",
            ],
        )
        writer.writeheader()

        for match in matches:
            # Add label_match column
            label_match = "✓" if match["docling_label"] == match["ground_truth_label"] else "✗"

            writer.writerow(
                {
                    "pdf_text": match["pdf_text"],
                    "html_text": match["html_text"],
                    "docling_label": match["docling_label"],
                    "docling_layer": match["docling_layer"],
                    "ground_truth_label": match["ground_truth_label"],
                    "match_score": f"{match['match_score']:.3f}",
                    "label_match": label_match,
                }
            )

    print(f"  📝 Exported to: {csv_path}")
    print(f"  Rows: {len(matches)}")


def analyze_and_export(pdf_path: Path, basename: str):
    """Analyze and export CSV for a single pair."""
    print(f"\n{'=' * 80}")
    print(f"PROCESSING: {basename}")
    print(f"{'=' * 80}\n")

    # Extract Docling labels
    print("Extracting Docling labels...")
    docling_items = extract_docling_labels(pdf_path)
    if not docling_items:
        print("⚠️  No Docling items extracted")
        return

    # Load ground truth
    print("Loading ground truth labels...")
    ground_truth_items = load_ground_truth_labels(basename)
    if not ground_truth_items:
        print("⚠️  No ground truth labels loaded")
        return

    print(f"Docling items: {len(docling_items)}")
    print(f"Ground truth items: {len(ground_truth_items)}\n")

    # Match items
    print("Matching items...")
    matches = match_items(docling_items, ground_truth_items)

    print(
        f"Matched: {len(matches)}/{len(docling_items)} ({len(matches) / len(docling_items) * 100:.1f}%)\n"
    )

    # Export to CSV
    export_csv(basename, matches)


def process_corpus():
    """Process all corpus pairs and export CSVs."""
    if not LABELED_HTML_DIR.exists() or not PDF_DIR.exists():
        print("❌ Directories not found")
        return

    labeled_files = sorted(LABELED_HTML_DIR.glob("*.json"))

    print("📊 EXPORTING LABEL COMPARISON CSVs")
    print(f"Found {len(labeled_files)} labeled files\n")
    print(f"Output directory: {OUTPUT_DIR}\n")

    for labeled_file in labeled_files:
        basename = labeled_file.stem
        pdf_file = PDF_DIR / f"{basename}.pdf"

        if not pdf_file.exists():
            print(f"⚠️  No PDF for {basename}")
            continue

        analyze_and_export(pdf_file, basename)

    print(f"\n{'=' * 80}")
    print("COMPLETE")
    print(f"{'=' * 80}")
    print(f"CSVs exported to: {OUTPUT_DIR}/")
    print(f"Total files: {len(list(OUTPUT_DIR.glob('*.csv')))}")


if __name__ == "__main__":
    process_corpus()
