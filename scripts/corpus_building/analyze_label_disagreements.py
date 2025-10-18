#!/usr/bin/env python3
"""
Analyze label disagreements between Docling and fuzzy matching.

Identifies cases where:
1. Docling labeled "footnote" → Fuzzy matched to body-text (GAINING body text!)
2. Docling labeled body text → Fuzzy matched to footnote (correcting contamination)

This helps determine if fine-tuning is needed or if Docling's automatic labeling is sufficient.

Output:
- Count of each disagreement type
- Statistics by article and overall
- Specific examples for manual review
- JSON file with all disagreements for further analysis

Author: Claude Code
Date: 2025-01-19
"""

import csv
import json
from pathlib import Path


def analyze_csv(csv_file: Path) -> dict:
    """
    Analyze a single CSV for label disagreements.

    Returns dict with:
    - fn_to_body: Count of "footnote" → body-text corrections (GAINING!)
    - body_to_fn: Count of body → footnote corrections
    - examples: List of specific disagreement cases
    """
    fn_to_body = 0
    body_to_fn = 0
    examples = []

    with open(csv_file, encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            # Only analyze matched rows (has both PDF and HTML)
            if row["match_status"] != "matched":
                continue

            pdf_label = row["pdf_original_label"]
            corrected_label = row["pdf_corrected_label"]

            # Skip if no correction happened
            if pdf_label == corrected_label:
                continue

            # Case 1: Docling said "footnote" → Actually body text (GAINING!)
            if "footnote" in pdf_label.lower() and corrected_label == "body_text":
                fn_to_body += 1
                examples.append(
                    {
                        "type": "fn_to_body",
                        "page_no": row["page_no"],
                        "pdf_text": row["pdf_text"][:200],  # First 200 chars
                        "pdf_original_label": pdf_label,
                        "pdf_corrected_label": corrected_label,
                        "match_confidence": float(row["match_confidence"]),
                    }
                )

            # Case 2: Docling said body → Actually footnote (contamination)
            elif "footnote" not in pdf_label.lower() and corrected_label == "footnote":
                body_to_fn += 1
                examples.append(
                    {
                        "type": "body_to_fn",
                        "page_no": row["page_no"],
                        "pdf_text": row["pdf_text"][:200],  # First 200 chars
                        "pdf_original_label": pdf_label,
                        "pdf_corrected_label": corrected_label,
                        "match_confidence": float(row["match_confidence"]),
                    }
                )

    return {
        "fn_to_body": fn_to_body,
        "body_to_fn": body_to_fn,
        "examples": examples,
    }


def main():
    """Analyze all CSVs for label disagreements."""
    csv_dir = Path("data/v3_data/v3_csv")
    csv_files = sorted(csv_dir.glob("*.csv"))

    print("=" * 80)
    print("Label Disagreement Analysis: Docling vs Fuzzy Matching")
    print("=" * 80)
    print()

    # Track overall statistics
    total_fn_to_body = 0
    total_body_to_fn = 0
    all_examples = []
    article_stats = []

    for idx, csv_file in enumerate(csv_files, 1):
        basename = csv_file.stem
        print(f"[{idx}/{len(csv_files)}] {basename}...", end=" ", flush=True)

        try:
            result = analyze_csv(csv_file)

            fn_to_body = result["fn_to_body"]
            body_to_fn = result["body_to_fn"]
            total_corrections = fn_to_body + body_to_fn

            # Print result
            if total_corrections == 0:
                print("✅ (0 disagreements)")
            else:
                print(
                    f"⚠️  ({fn_to_body} fn→body, {body_to_fn} body→fn = {total_corrections} total)"
                )

            # Update totals
            total_fn_to_body += fn_to_body
            total_body_to_fn += body_to_fn
            all_examples.extend(result["examples"])

            # Track per-article stats
            article_stats.append(
                {
                    "basename": basename,
                    "fn_to_body": fn_to_body,
                    "body_to_fn": body_to_fn,
                    "total_corrections": total_corrections,
                }
            )

        except Exception as e:
            print(f"❌ Error: {e}")

    # Print summary
    print()
    print("=" * 80)
    print("Summary Statistics")
    print("=" * 80)
    print(f"Total disagreements: {total_fn_to_body + total_body_to_fn:,}")
    print()
    print(f"  fn → body (GAINING body text!): {total_fn_to_body:,}")
    print(f"  body → fn (correcting contamination): {total_body_to_fn:,}")
    print()

    # Calculate percentages
    total_corrections = total_fn_to_body + total_body_to_fn
    if total_corrections > 0:
        fn_to_body_pct = (total_fn_to_body / total_corrections) * 100
        body_to_fn_pct = (total_body_to_fn / total_corrections) * 100
        print(f"  fn → body: {fn_to_body_pct:.1f}% of all corrections")
        print(f"  body → fn: {body_to_fn_pct:.1f}% of all corrections")
        print()

    # Top offenders
    print("Articles with most disagreements:")
    top_articles = sorted(article_stats, key=lambda x: x["total_corrections"], reverse=True)[:10]
    for article in top_articles:
        if article["total_corrections"] > 0:
            print(
                f"  {article['basename']}: {article['total_corrections']} "
                f"({article['fn_to_body']} fn→body, {article['body_to_fn']} body→fn)"
            )
    print()

    # Save detailed results to JSON
    output_file = Path("data/v3_data/label_disagreements.json")
    output = {
        "summary": {
            "total_disagreements": total_corrections,
            "fn_to_body_count": total_fn_to_body,
            "body_to_fn_count": total_body_to_fn,
            "fn_to_body_pct": fn_to_body_pct if total_corrections > 0 else 0,
            "body_to_fn_pct": body_to_fn_pct if total_corrections > 0 else 0,
        },
        "article_stats": article_stats,
        "examples": all_examples,
    }

    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)

    print(f"✅ Detailed results saved to: {output_file}")
    print()

    # Recommendation
    print("=" * 80)
    print("Recommendation")
    print("=" * 80)
    if total_corrections == 0:
        print("✅ Perfect alignment! Docling's automatic labeling matches fuzzy matching.")
        print("   No fine-tuning needed.")
    elif total_corrections < 100:
        print(
            f"⚠️  Minor disagreements ({total_corrections} corrections across {len(csv_files)} articles)."
        )
        print("   Review examples to determine if fine-tuning would help.")
    else:
        print(
            f"⚠️  Significant disagreements ({total_corrections} corrections across {len(csv_files)} articles)."
        )
        print("   Fine-tuning recommended to capture systematic correction patterns.")
        print()
        print("   Key benefit:")
        print(f"   - GAINING {total_fn_to_body:,} body text samples that would have been lost!")
        print(f"   - Correcting {total_body_to_fn:,} contaminated samples")


if __name__ == "__main__":
    main()
