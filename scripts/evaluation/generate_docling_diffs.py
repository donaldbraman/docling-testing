#!/usr/bin/env python3
"""
Generate visual diffs comparing Docling predictions to HTML ground truth.

Creates markdown files showing:
- What text Docling captured vs. missed
- Label assignments (body-text, footnote-text, other)
- Coverage statistics per document
"""

import json
import re
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
    """Extract the Docling label from the repr string."""
    match = re.search(r"label=<DocItemLabel\.\w+: '([^']+)'>", text_repr)
    if match:
        return match.group(1)
    return "unknown"


def extract_text_from_repr(text_repr: str) -> str:
    """Extract the text content from the repr string."""
    match = re.search(r"text='([^']*(?:''[^']*)*)'", text_repr)
    if match:
        return match.group(1).replace("\\'", "'")
    return ""


def truncate_text(text: str, max_len: int = 100) -> str:
    """Truncate text for display."""
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."


def generate_diff_markdown(
    pdf_name: str,
    pdf_texts: list[tuple[str, str, str]],  # (docling_label, target_label, text)
    html_body: list[str],
    html_footnotes: list[str],
    coverage_metrics: dict,
) -> str:
    """Generate a markdown diff for one document."""

    lines = []
    lines.append(f"# Docling Coverage Analysis: {pdf_name}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Summary statistics
    lines.append("## Coverage Summary")
    lines.append("")
    lines.append(f"- **Overall Coverage:** {coverage_metrics['overall_coverage']:.1%}")
    lines.append(f"- **Body Coverage:** {coverage_metrics['body_coverage']:.1%}")
    lines.append(f"- **Footnote Coverage:** {coverage_metrics['footnote_coverage']:.1%}")
    lines.append("")
    lines.append("### Character Counts")
    lines.append("")
    lines.append("| Type | PDF Extracted | HTML Ground Truth | Coverage |")
    lines.append("|------|---------------|-------------------|----------|")
    lines.append(
        f"| Body | {coverage_metrics['pdf_body_chars']:,} | {coverage_metrics['html_body_chars']:,} | {coverage_metrics['body_coverage']:.1%} |"
    )
    lines.append(
        f"| Footnotes | {coverage_metrics['pdf_footnote_chars']:,} | {coverage_metrics['html_footnote_chars']:,} | {coverage_metrics['footnote_coverage']:.1%} |"
    )
    lines.append(f"| Other | {coverage_metrics['pdf_other_chars']:,} | — | — |")
    lines.append("")

    # Line counts
    lines.append("### Line Counts")
    lines.append("")
    lines.append(f"- **Body lines:** {coverage_metrics['num_body_lines']}")
    lines.append(f"- **Footnote lines:** {coverage_metrics['num_footnote_lines']}")
    lines.append(f"- **Other lines:** {coverage_metrics['num_other_lines']}")
    lines.append(
        f"- **Total PDF lines:** {coverage_metrics['num_body_lines'] + coverage_metrics['num_footnote_lines'] + coverage_metrics['num_other_lines']}"
    )
    lines.append("")

    lines.append("---")
    lines.append("")

    # Docling extraction sample
    lines.append("## Docling Extraction Sample (First 20 lines)")
    lines.append("")
    lines.append("| # | Docling Label | Target Label | Text (truncated) |")
    lines.append("|---|---------------|--------------|------------------|")

    for i, (docling_label, target_label, text) in enumerate(pdf_texts[:20], 1):
        text_display = truncate_text(text, 80).replace("|", "\\|")
        lines.append(f"| {i} | `{docling_label}` | `{target_label}` | {text_display} |")

    if len(pdf_texts) > 20:
        lines.append(f"| ... | ... | ... | *({len(pdf_texts) - 20} more lines)* |")

    lines.append("")
    lines.append("---")
    lines.append("")

    # HTML ground truth sample
    lines.append("## HTML Ground Truth Sample")
    lines.append("")
    lines.append("### Body Text (First 10 paragraphs)")
    lines.append("")

    for i, para in enumerate(html_body[:10], 1):
        text_display = truncate_text(para, 150).replace("|", "\\|")
        lines.append(f"{i}. {text_display}")
        lines.append("")

    if len(html_body) > 10:
        lines.append(f"*...and {len(html_body) - 10} more body paragraphs*")
        lines.append("")

    lines.append("### Footnotes (First 10)")
    lines.append("")

    if html_footnotes:
        for i, note in enumerate(html_footnotes[:10], 1):
            text_display = truncate_text(note, 150).replace("|", "\\|")
            lines.append(f"{i}. {text_display}")
            lines.append("")

        if len(html_footnotes) > 10:
            lines.append(f"*...and {len(html_footnotes) - 10} more footnotes*")
            lines.append("")
    else:
        lines.append("*No footnotes in ground truth*")
        lines.append("")

    lines.append("---")
    lines.append("")

    # Text comparison
    lines.append("## Full Text Comparison")
    lines.append("")

    # Body text
    pdf_body = " ".join([text for _, label, text in pdf_texts if label == "body-text"])
    html_body_full = " ".join(html_body)

    lines.append("### Body Text")
    lines.append("")
    lines.append(f"**PDF extracted ({len(pdf_body):,} chars):**")
    lines.append("```")
    lines.append(pdf_body[:500])
    if len(pdf_body) > 500:
        lines.append("...")
    lines.append("```")
    lines.append("")

    lines.append(f"**HTML ground truth ({len(html_body_full):,} chars):**")
    lines.append("```")
    lines.append(html_body_full[:500])
    if len(html_body_full) > 500:
        lines.append("...")
    lines.append("```")
    lines.append("")

    # Footnotes
    pdf_footnotes = " ".join([text for _, label, text in pdf_texts if label == "footnote-text"])
    html_footnotes_full = " ".join(html_footnotes)

    lines.append("### Footnote Text")
    lines.append("")
    lines.append(f"**PDF extracted ({len(pdf_footnotes):,} chars):**")
    lines.append("```")
    lines.append(pdf_footnotes[:500] if pdf_footnotes else "(none)")
    if len(pdf_footnotes) > 500:
        lines.append("...")
    lines.append("```")
    lines.append("")

    lines.append(f"**HTML ground truth ({len(html_footnotes_full):,} chars):**")
    lines.append("```")
    lines.append(html_footnotes_full[:500] if html_footnotes_full else "(none)")
    if len(html_footnotes_full) > 500:
        lines.append("...")
    lines.append("```")
    lines.append("")

    # Label distribution
    lines.append("---")
    lines.append("")
    lines.append("## Label Distribution Analysis")
    lines.append("")

    docling_label_counts = {}
    for docling_label, _, _ in pdf_texts:
        docling_label_counts[docling_label] = docling_label_counts.get(docling_label, 0) + 1

    target_label_counts = {}
    for _, target_label, _ in pdf_texts:
        target_label_counts[target_label] = target_label_counts.get(target_label, 0) + 1

    lines.append("### Docling Original Labels")
    lines.append("")
    for label, count in sorted(docling_label_counts.items(), key=lambda x: x[1], reverse=True):
        pct = 100 * count / len(pdf_texts)
        lines.append(f"- `{label}`: {count} lines ({pct:.1f}%)")
    lines.append("")

    lines.append("### After Preprocessing (Target Labels)")
    lines.append("")
    for label, count in sorted(target_label_counts.items(), key=lambda x: x[1], reverse=True):
        pct = 100 * count / len(pdf_texts)
        lines.append(f"- `{label}`: {count} lines ({pct:.1f}%)")
    lines.append("")

    return "\n".join(lines)


def calculate_content_coverage(
    pdf_texts: list[tuple[str, str]], html_body: list[str], html_footnotes: list[str]
) -> dict[str, float]:
    """Calculate content coverage metrics."""
    pdf_body_texts = [text for label, text in pdf_texts if label == "body-text"]
    pdf_footnote_texts = [text for label, text in pdf_texts if label == "footnote-text"]
    pdf_other_texts = [text for label, text in pdf_texts if label == "other"]

    full_pdf_body = " ".join(pdf_body_texts)
    full_pdf_footnotes = " ".join(pdf_footnote_texts)
    full_html_body = " ".join(html_body)
    full_html_footnotes = " ".join(html_footnotes)

    norm_pdf_body = normalize_text(full_pdf_body)
    norm_pdf_footnotes = normalize_text(full_pdf_footnotes)
    norm_html_body = normalize_text(full_html_body)
    norm_html_footnotes = normalize_text(full_html_footnotes)

    body_coverage = fuzz.ratio(norm_pdf_body, norm_html_body) / 100.0
    footnote_coverage = fuzz.ratio(norm_pdf_footnotes, norm_html_footnotes) / 100.0

    html_total_chars = len(norm_html_body) + len(norm_html_footnotes)
    if html_total_chars > 0:
        body_weight = len(norm_html_body) / html_total_chars
        footnote_weight = len(norm_html_footnotes) / html_total_chars
        overall_coverage = (body_coverage * body_weight) + (footnote_coverage * footnote_weight)
    else:
        overall_coverage = 0.0

    return {
        "body_coverage": body_coverage,
        "footnote_coverage": footnote_coverage,
        "overall_coverage": overall_coverage,
        "pdf_body_chars": len(norm_pdf_body),
        "pdf_footnote_chars": len(norm_pdf_footnotes),
        "pdf_other_chars": len(" ".join(pdf_other_texts)),
        "html_body_chars": len(norm_html_body),
        "html_footnote_chars": len(norm_html_footnotes),
        "num_body_lines": len(pdf_body_texts),
        "num_footnote_lines": len(pdf_footnote_texts),
        "num_other_lines": len(pdf_other_texts),
    }


def process_pdf(extraction_path: Path, ground_truth_path: Path, output_dir: Path):
    """Process one PDF and generate diff."""
    pdf_name = extraction_path.stem.replace("_baseline_extraction", "")

    # Load data
    with open(extraction_path) as f:
        extraction_data = json.load(f)

    with open(ground_truth_path) as f:
        gt_data = json.load(f)

    # Parse extractions
    pdf_texts_full = []  # (docling_label, target_label, text)
    pdf_texts_simple = []  # (target_label, text) for coverage

    for text_repr in extraction_data["texts"]:
        docling_label = extract_label_from_repr(text_repr)
        text_content = extract_text_from_repr(text_repr)
        target_label = preprocess_docling_label(docling_label)
        pdf_texts_full.append((docling_label, target_label, text_content))
        pdf_texts_simple.append((target_label, text_content))

    # Get ground truth
    html_body = [p["text"] for p in gt_data["body_text_paragraphs"]]
    html_footnotes = [p["text"] for p in gt_data.get("footnotes", [])]

    # Calculate coverage
    coverage = calculate_content_coverage(pdf_texts_simple, html_body, html_footnotes)

    # Generate diff markdown
    diff_md = generate_diff_markdown(pdf_name, pdf_texts_full, html_body, html_footnotes, coverage)

    # Write to file
    output_file = output_dir / f"{pdf_name}_docling_diff.md"
    with open(output_file, "w") as f:
        f.write(diff_md)

    print(f"✅ Generated diff: {output_file.name}")
    return coverage["overall_coverage"]


def main():
    # Paths
    extraction_dir = Path("results/ocr_pipeline_evaluation/extractions")
    gt_dir = Path("results/ocr_pipeline_evaluation/ground_truth")
    output_dir = Path("results/ocr_pipeline_evaluation/docling_diffs")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Find all baseline extractions
    extraction_files = sorted(extraction_dir.glob("*_baseline_extraction.json"))

    print(f"Generating diffs for {len(extraction_files)} PDFs...\n")

    coverages = []
    for extraction_path in extraction_files:
        pdf_name = extraction_path.stem.replace("_baseline_extraction", "")
        gt_path = gt_dir / f"{pdf_name}_ground_truth.json"

        if not gt_path.exists():
            print(f"⚠️  Skipping {pdf_name}: ground truth not found")
            continue

        coverage = process_pdf(extraction_path, gt_path, output_dir)
        coverages.append((pdf_name, coverage))

    print(f"\n{'=' * 60}")
    print("Summary of Coverage (sorted by coverage)")
    print(f"{'=' * 60}")

    for pdf_name, coverage in sorted(coverages, key=lambda x: x[1], reverse=True):
        print(f"{coverage:5.1%} - {pdf_name}")

    print(f"\n✅ All diffs saved to: {output_dir}")
    print(f"📄 Generated {len(coverages)} diff files")


if __name__ == "__main__":
    main()
