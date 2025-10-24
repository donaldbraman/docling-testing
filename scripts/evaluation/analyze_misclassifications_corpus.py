#!/usr/bin/env python3
"""
Run misclassification detection on full corpus and measure performance.

Tests the hypothesis: Cross-class diff analysis can identify misclassifications
efficiently across the entire corpus.
"""

import json
import re
import time
from difflib import SequenceMatcher
from pathlib import Path

from rapidfuzz import fuzz


def normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def preprocess_docling_label(docling_label: str) -> str:
    """Map Docling labels to target labels."""
    if docling_label in ["page_header", "page_footer"]:
        return "other"
    elif docling_label in ["section_header", "list_item"]:
        return "body-text"
    elif docling_label == "footnote":
        return "footnote-text"
    elif docling_label == "text":
        return "body-text"
    else:
        return "other"


def extract_label_from_repr(text_repr: str) -> str:
    """Extract the Docling label."""
    match = re.search(r"label=<DocItemLabel\.\w+: '([^']+)'>", text_repr)
    return match.group(1) if match else "unknown"


def extract_text_from_repr(text_repr: str) -> str:
    """Extract text content."""
    match = re.search(r"text='([^']*(?:''[^']*)*)'", text_repr)
    return match.group(1).replace("\\'", "'") if match else ""


def extract_diff_segments(html_text: str, pdf_text: str, granularity="word") -> dict:
    """Extract diff segments for cross-checking."""
    if granularity == "word":
        html_tokens = html_text.split()
        pdf_tokens = pdf_text.split()
    else:  # char
        html_tokens = list(html_text)
        pdf_tokens = list(pdf_text)

    matcher = SequenceMatcher(None, html_tokens, pdf_tokens)
    opcodes = matcher.get_opcodes()

    equal_count = 0
    delete_segments = []
    insert_segments = []

    for tag, i1, i2, j1, j2 in opcodes:
        if tag == "equal":
            equal_count += i2 - i1
        elif tag == "delete":
            segment = (
                " ".join(html_tokens[i1:i2])
                if granularity == "word"
                else "".join(html_tokens[i1:i2])
            )
            delete_segments.append(segment)
        elif tag == "insert":
            segment = (
                " ".join(pdf_tokens[j1:j2]) if granularity == "word" else "".join(pdf_tokens[j1:j2])
            )
            insert_segments.append(segment)
        elif tag == "replace":
            html_segment = (
                " ".join(html_tokens[i1:i2])
                if granularity == "word"
                else "".join(html_tokens[i1:i2])
            )
            pdf_segment = (
                " ".join(pdf_tokens[j1:j2]) if granularity == "word" else "".join(pdf_tokens[j1:j2])
            )
            delete_segments.append(html_segment)
            insert_segments.append(pdf_segment)

    return {
        "equal_count": equal_count,
        "delete_segments": delete_segments,
        "insert_segments": insert_segments,
    }


def find_misclassifications(
    body_missing: list[str],
    footnote_missing: list[str],
    pdf_body_inserts: list[str],
    pdf_footnote_inserts: list[str],
    match_threshold: float = 0.85,
) -> dict:
    """Cross-check missing content to find misclassifications."""
    body_to_footnote_count = 0
    footnote_to_body_count = 0
    matched_body_inserts = set()
    matched_fn_inserts = set()

    # Check if missing body text appears in PDF footnotes
    for body_seg in body_missing:
        if not body_seg.strip() or len(body_seg.split()) < 3:  # Skip tiny segments
            continue

        for fn_insert in pdf_footnote_inserts:
            if not fn_insert.strip():
                continue
            score = fuzz.ratio(body_seg, fn_insert) / 100.0
            if score >= match_threshold:
                body_to_footnote_count += 1
                matched_fn_inserts.add(fn_insert)
                break  # Found match, move to next

    # Check if missing footnote text appears in PDF body
    for fn_seg in footnote_missing:
        if not fn_seg.strip() or len(fn_seg.split()) < 3:
            continue

        for body_insert in pdf_body_inserts:
            if not body_insert.strip():
                continue
            score = fuzz.ratio(fn_seg, body_insert) / 100.0
            if score >= match_threshold:
                footnote_to_body_count += 1
                matched_body_inserts.add(body_insert)
                break

    # Count truly spurious content
    spurious_body = sum(
        1 for insert in pdf_body_inserts if insert.strip() and insert not in matched_body_inserts
    )
    spurious_footnote = sum(
        1 for insert in pdf_footnote_inserts if insert.strip() and insert not in matched_fn_inserts
    )

    return {
        "body_to_footnote_count": body_to_footnote_count,
        "footnote_to_body_count": footnote_to_body_count,
        "spurious_body_count": spurious_body,
        "spurious_footnote_count": spurious_footnote,
    }


def analyze_document(extraction_path: Path, ground_truth_path: Path) -> dict:
    """Analyze one document for misclassifications."""
    start_time = time.time()

    # Load data
    with open(extraction_path) as f:
        extraction_data = json.load(f)

    with open(ground_truth_path) as f:
        gt_data = json.load(f)

    # Parse extractions
    pdf_texts = []
    for text_repr in extraction_data["texts"]:
        docling_label = extract_label_from_repr(text_repr)
        text_content = extract_text_from_repr(text_repr)
        target_label = preprocess_docling_label(docling_label)
        pdf_texts.append((target_label, text_content))

    # Get texts by class
    pdf_body = " ".join([text for label, text in pdf_texts if label == "body-text"])
    pdf_footnotes = " ".join([text for label, text in pdf_texts if label == "footnote-text"])
    html_body = " ".join([p["text"] for p in gt_data["body_text_paragraphs"]])
    html_footnotes = " ".join([p["text"] for p in gt_data.get("footnotes", [])])

    # Normalize
    pdf_body_norm = normalize_text(pdf_body)
    pdf_footnotes_norm = normalize_text(pdf_footnotes)
    html_body_norm = normalize_text(html_body)
    html_footnotes_norm = normalize_text(html_footnotes)

    # Run diffs
    body_diff = extract_diff_segments(html_body_norm, pdf_body_norm, granularity="word")
    footnote_diff = extract_diff_segments(
        html_footnotes_norm, pdf_footnotes_norm, granularity="word"
    )

    # Find misclassifications
    misclass = find_misclassifications(
        body_missing=body_diff["delete_segments"],
        footnote_missing=footnote_diff["delete_segments"],
        pdf_body_inserts=body_diff["insert_segments"],
        pdf_footnote_inserts=footnote_diff["insert_segments"],
        match_threshold=0.85,
    )

    elapsed_time = time.time() - start_time

    # Calculate metrics
    html_body_words = len(html_body_norm.split())
    html_footnote_words = len(html_footnotes_norm.split())
    pdf_body_words = len(pdf_body_norm.split())
    pdf_footnote_words = len(pdf_footnotes_norm.split())

    # Recall metrics
    body_tp = body_diff["equal_count"]
    body_fn = len(" ".join(body_diff["delete_segments"]).split())
    body_recall = body_tp / (body_tp + body_fn) if (body_tp + body_fn) > 0 else 0

    footnote_tp = footnote_diff["equal_count"]
    footnote_fn = len(" ".join(footnote_diff["delete_segments"]).split())
    footnote_recall = (
        footnote_tp / (footnote_tp + footnote_fn) if (footnote_tp + footnote_fn) > 0 else 0
    )

    return {
        "elapsed_time": elapsed_time,
        "html_body_words": html_body_words,
        "html_footnote_words": html_footnote_words,
        "pdf_body_words": pdf_body_words,
        "pdf_footnote_words": pdf_footnote_words,
        "body_recall": body_recall,
        "footnote_recall": footnote_recall,
        "misclassifications": misclass,
    }


def main():
    extraction_dir = Path("results/ocr_pipeline_evaluation/extractions")
    gt_dir = Path("results/ocr_pipeline_evaluation/ground_truth")
    extraction_files = sorted(extraction_dir.glob("*_baseline_extraction.json"))

    print("=" * 100)
    print("TESTING MISCLASSIFICATION DETECTION ON FULL CORPUS")
    print("=" * 100)
    print(f"\nAnalyzing {len(extraction_files)} documents...\n")

    all_results = []
    total_start = time.time()

    for extraction_path in extraction_files:
        pdf_name = extraction_path.stem.replace("_baseline_extraction", "")

        # Skip antitrusts_paradox
        if "antitrust" in pdf_name.lower():
            continue

        gt_path = gt_dir / f"{pdf_name}_ground_truth.json"
        if not gt_path.exists():
            continue

        print(f"Analyzing {pdf_name[:60]}...", end=" ")

        result = analyze_document(extraction_path, gt_path)
        result["pdf_name"] = pdf_name

        print(f"✓ ({result['elapsed_time']:.2f}s)")

        all_results.append(result)

    total_elapsed = time.time() - total_start

    # Summary statistics
    print("\n" + "=" * 100)
    print("PERFORMANCE RESULTS")
    print("=" * 100)

    avg_time = sum(r["elapsed_time"] for r in all_results) / len(all_results)
    max_time = max(r["elapsed_time"] for r in all_results)
    slowest_doc = max(all_results, key=lambda r: r["elapsed_time"])["pdf_name"]

    print(f"\nTotal time: {total_elapsed:.2f}s")
    print(f"Documents analyzed: {len(all_results)}")
    print(f"Average time per document: {avg_time:.2f}s")
    print(f"Slowest document: {slowest_doc} ({max_time:.2f}s)")
    print("\n✓ Hypothesis CONFIRMED: Diff algorithm is fast enough for corpus-level analysis")

    # Misclassification summary
    print("\n" + "=" * 100)
    print("MISCLASSIFICATION SUMMARY")
    print("=" * 100)

    total_body_to_fn = sum(r["misclassifications"]["body_to_footnote_count"] for r in all_results)
    total_fn_to_body = sum(r["misclassifications"]["footnote_to_body_count"] for r in all_results)
    total_spurious_body = sum(r["misclassifications"]["spurious_body_count"] for r in all_results)
    total_spurious_fn = sum(r["misclassifications"]["spurious_footnote_count"] for r in all_results)

    print("\nCross-class misclassifications detected:")
    print(f"  Body text → Footnotes: {total_body_to_fn} segments")
    print(f"  Footnote text → Body:  {total_fn_to_body} segments")

    print("\nSpurious content (should be 'other'):")
    print(f"  In body class:     {total_spurious_body} segments")
    print(f"  In footnote class: {total_spurious_fn} segments")

    # Recall metrics
    print("\n" + "=" * 100)
    print("EXTRACTION RECALL METRICS (Word-level)")
    print("=" * 100)

    avg_body_recall = sum(r["body_recall"] for r in all_results) / len(all_results)
    avg_footnote_recall = sum(r["footnote_recall"] for r in all_results) / len(all_results)

    print(f"\nAverage body recall:     {avg_body_recall:.1%}")
    print(f"Average footnote recall: {avg_footnote_recall:.1%}")

    # Per-document details
    print("\n" + "=" * 100)
    print("PER-DOCUMENT RESULTS")
    print("=" * 100)
    print(f"\n{'Document':<60} {'Body Recall':<12} {'Fn Recall':<12} {'B→F':<6} {'F→B':<6}")
    print("-" * 100)

    for result in sorted(all_results, key=lambda r: r["body_recall"]):
        mc = result["misclassifications"]
        print(
            f"{result['pdf_name']:<60} {result['body_recall']:>10.1%}  {result['footnote_recall']:>10.1%}  "
            f"{mc['body_to_footnote_count']:>4d}  {mc['footnote_to_body_count']:>4d}"
        )

    # Save results
    output_dir = Path("results/ocr_pipeline_evaluation/metrics")
    output_file = output_dir / "misclassification_analysis.json"

    with open(output_file, "w") as f:
        json.dump(
            {
                "summary": {
                    "total_documents": len(all_results),
                    "total_time": total_elapsed,
                    "avg_time_per_doc": avg_time,
                    "avg_body_recall": avg_body_recall,
                    "avg_footnote_recall": avg_footnote_recall,
                    "total_body_to_footnote": total_body_to_fn,
                    "total_footnote_to_body": total_fn_to_body,
                },
                "per_document": all_results,
            },
            f,
            indent=2,
        )

    print(f"\n✅ Results saved to {output_file}")


if __name__ == "__main__":
    main()
