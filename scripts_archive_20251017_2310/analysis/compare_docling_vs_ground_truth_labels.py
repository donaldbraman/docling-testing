#!/usr/bin/env python3
"""Compare Docling's labels vs our ground truth labels across corpus."""

import json
from collections import Counter, defaultdict
from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import LayoutOptions, PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption

LABELED_HTML_DIR = Path("data/labeled_html")
PDF_DIR = Path("data/raw_pdf")
CACHE_DIR = Path("data/extraction_cache")


def normalize_text(text: str) -> str:
    """Normalize text for matching."""
    import re

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


def fuzzy_match_texts(text1: str, text2: str, threshold: float = 0.85) -> bool:
    """Check if two texts are similar enough to be the same."""
    from rapidfuzz import fuzz

    # Exact match
    if text1 == text2:
        return True

    # Fuzzy match
    score = fuzz.ratio(text1, text2) / 100.0
    return score >= threshold


def match_items(docling_items: list[dict], ground_truth_items: list[dict]) -> list[dict]:
    """Match Docling items to ground truth items."""
    matches = []

    for doc_item in docling_items:
        best_match = None
        best_score = 0

        for gt_item in ground_truth_items:
            if fuzzy_match_texts(doc_item["text"], gt_item["text"], threshold=0.85):
                from rapidfuzz import fuzz

                score = fuzz.ratio(doc_item["text"], gt_item["text"]) / 100.0
                if score > best_score:
                    best_score = score
                    best_match = gt_item

        if best_match:
            matches.append(
                {
                    "text": doc_item["text"][:100] + "..."
                    if len(doc_item["text"]) > 100
                    else doc_item["text"],
                    "docling_label": doc_item["label"],
                    "docling_layer": doc_item["layer"],
                    "ground_truth_label": best_match["label"],
                    "match_score": best_score,
                }
            )

    return matches


def analyze_pair(pdf_path: Path, basename: str):
    """Analyze label differences for a single pair."""
    print(f"\n{'=' * 80}")
    print(f"ANALYZING: {basename}")
    print(f"{'=' * 80}\n")

    # Extract Docling labels
    print("Extracting Docling labels...")
    docling_items = extract_docling_labels(pdf_path)
    if not docling_items:
        print("⚠️  No Docling items extracted")
        return None

    # Load ground truth
    print("Loading ground truth labels...")
    ground_truth_items = load_ground_truth_labels(basename)
    if not ground_truth_items:
        print("⚠️  No ground truth labels loaded")
        return None

    print(f"Docling items: {len(docling_items)}")
    print(f"Ground truth items: {len(ground_truth_items)}\n")

    # Match items
    print("Matching items...")
    matches = match_items(docling_items, ground_truth_items)

    print(
        f"Matched: {len(matches)}/{len(docling_items)} ({len(matches) / len(docling_items) * 100:.1f}%)\n"
    )

    # Analyze label disagreements
    disagreements = [m for m in matches if m["docling_label"] != m["ground_truth_label"]]

    if disagreements:
        print(f"🔍 LABEL DISAGREEMENTS: {len(disagreements)}")
        print("=" * 80)

        # Group by disagreement type
        by_type = defaultdict(list)
        for d in disagreements:
            key = (d["docling_label"], d["ground_truth_label"])
            by_type[key].append(d)

        for (docling_label, gt_label), items in sorted(by_type.items(), key=lambda x: -len(x[1])):
            print(f"\n[{len(items)}x] Docling: '{docling_label}' → Our label: '{gt_label}'")
            print("-" * 80)
            for item in items[:3]:  # Show first 3 examples
                print(f"  Text: {item['text']}")
                print(f"  Match: {item['match_score']:.1%}")
                print()
    else:
        print("✅ No label disagreements!\n")

    # Build disagreement types dict
    disagreement_types = {}
    if disagreements:
        types_dict = defaultdict(list)
        for m in disagreements:
            key = (m["docling_label"], m["ground_truth_label"])
            types_dict[key].append(m)
        disagreement_types = {
            f"{d_label} → {gt_label}": len(items)
            for (d_label, gt_label), items in types_dict.items()
        }

    return {
        "basename": basename,
        "docling_items": len(docling_items),
        "ground_truth_items": len(ground_truth_items),
        "matches": len(matches),
        "disagreements": len(disagreements),
        "disagreement_types": disagreement_types,
    }


def analyze_corpus():
    """Analyze all corpus pairs."""
    if not LABELED_HTML_DIR.exists() or not PDF_DIR.exists():
        print("❌ Directories not found")
        return

    labeled_files = sorted(LABELED_HTML_DIR.glob("*.json"))

    print("🔍 COMPARING DOCLING LABELS VS GROUND TRUTH")
    print(f"Found {len(labeled_files)} labeled files\n")

    results = []

    for labeled_file in labeled_files:
        basename = labeled_file.stem
        pdf_file = PDF_DIR / f"{basename}.pdf"

        if not pdf_file.exists():
            print(f"⚠️  No PDF for {basename}")
            continue

        result = analyze_pair(pdf_file, basename)
        if result:
            results.append(result)

    # Summary
    print(f"\n{'=' * 80}")
    print("SUMMARY ACROSS ALL PAIRS")
    print(f"{'=' * 80}\n")

    total_disagreements = sum(r["disagreements"] for r in results)
    total_matches = sum(r["matches"] for r in results)

    print(f"Total pairs analyzed: {len(results)}")
    print(f"Total matches: {total_matches:,}")
    print(
        f"Total disagreements: {total_disagreements:,} ({total_disagreements / total_matches * 100:.1f}%)\n"
    )

    if total_disagreements > 0:
        # Aggregate disagreement types
        all_types = Counter()
        for r in results:
            for dtype, count in r.get("disagreement_types", {}).items():
                all_types[dtype] += count

        print("Most common label disagreements:")
        print("-" * 80)
        for dtype, count in all_types.most_common(10):
            print(f"  [{count:>4}x] {dtype}")


if __name__ == "__main__":
    analyze_corpus()
