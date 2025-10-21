#!/usr/bin/env python3
"""
Check if footnote text is contaminating body text in HTML ground truth.

Common issue: Footnote markers in HTML often contain the footnote text
within <a> tags or similar, which our parser might be including in body text.
"""

import json
import re
from pathlib import Path


def check_text_overlap(body_text: str, footnote_text: str) -> dict:
    """Check if footnote text appears within body text."""

    body_lower = body_text.lower()
    footnote_lower = footnote_text.lower()

    # Check if footnote text appears in body
    overlap_chars = 0
    footnote_words = footnote_lower.split()

    # Check for significant chunks (5+ words) of footnote text in body
    overlaps = []
    for i in range(len(footnote_words) - 4):
        chunk = " ".join(footnote_words[i : i + 5])
        if chunk in body_lower:
            overlaps.append(chunk)
            overlap_chars += len(chunk)

    return {
        "total_footnote_chars": len(footnote_text),
        "overlap_chars": overlap_chars,
        "overlap_percentage": 100 * overlap_chars / len(footnote_text)
        if len(footnote_text) > 0
        else 0,
        "overlapping_chunks": overlaps[:5],  # Show first 5
    }


def analyze_document(ground_truth_path: Path) -> dict:
    """Analyze one document for footnote contamination."""

    with open(ground_truth_path) as f:
        gt_data = json.load(f)

    # Get body and footnote paragraphs
    body_paragraphs = gt_data.get("body_text_paragraphs", [])
    footnote_paragraphs = gt_data.get("footnotes", [])

    # Concatenate all text
    body_text = " ".join([p["text"] for p in body_paragraphs])
    footnote_text = " ".join([p["text"] for p in footnote_paragraphs])

    # Check for overlap
    overlap = check_text_overlap(body_text, footnote_text)

    # Also check individual footnotes
    contaminated_footnotes = []
    for i, fn_para in enumerate(footnote_paragraphs[:10]):  # Check first 10
        fn_text = fn_para["text"]
        if fn_text.lower() in body_text.lower():
            contaminated_footnotes.append(
                {"index": i, "text": fn_text[:100], "length": len(fn_text)}
            )

    return {
        "body_paragraphs": len(body_paragraphs),
        "footnote_paragraphs": len(footnote_paragraphs),
        "body_chars": len(body_text),
        "footnote_chars": len(footnote_text),
        "overlap": overlap,
        "contaminated_footnotes": contaminated_footnotes,
    }


def inspect_raw_html(html_path: Path) -> dict:
    """Inspect raw HTML structure for footnote markers."""

    if not html_path.exists():
        return {"found": False}

    with open(html_path) as f:
        html_content = f.read()

    # Look for common footnote patterns
    patterns = {
        "footnote_markers": re.findall(
            r'<a[^>]*class=["\'][^"\']*footnote[^"\']*["\'][^>]*>.*?</a>',
            html_content,
            re.IGNORECASE,
        )[:5],
        "sup_tags": re.findall(r"<sup[^>]*>.*?</sup>", html_content)[:5],
        "footnote_refs": re.findall(r'<a[^>]*href=["\']#fn[^"\']*["\'][^>]*>.*?</a>', html_content)[
            :5
        ],
    }

    return {
        "found": True,
        "sample_patterns": patterns,
    }


def main():
    gt_dir = Path("results/ocr_pipeline_evaluation/ground_truth")
    html_dir = Path("data/v3_data/processed_html")

    gt_files = sorted(gt_dir.glob("*_ground_truth.json"))

    print("=" * 120)
    print("CHECKING FOR FOOTNOTE CONTAMINATION IN HTML GROUND TRUTH")
    print("=" * 120)
    print("\nLooking for footnote text embedded in body text markers\n")

    results = []

    for gt_path in gt_files:
        pdf_name = gt_path.stem.replace("_ground_truth", "")

        # Skip antitrusts_paradox
        if "antitrust" in pdf_name.lower():
            continue

        result = analyze_document(gt_path)
        result["pdf_name"] = pdf_name
        results.append(result)

        # Also check raw HTML if available
        html_path = html_dir / f"{pdf_name}.html"
        if html_path.exists():
            result["raw_html"] = inspect_raw_html(html_path)

    # Print results
    print("-" * 120)
    print("OVERLAP ANALYSIS (footnote text found in body text)")
    print("-" * 120)
    print(f"\n{'Document':<62} {'FN Chars':<10} {'Overlap %':<12} {'Contaminated':<12}")
    print("-" * 120)

    for result in sorted(results, key=lambda r: r["overlap"]["overlap_percentage"], reverse=True):
        overlap_pct = result["overlap"]["overlap_percentage"]
        contaminated_count = len(result["contaminated_footnotes"])

        marker = "⚠️" if overlap_pct > 10 else ""

        print(
            f"{result['pdf_name']:<62} "
            f"{result['footnote_chars']:>8,}  "
            f"{overlap_pct:>10.1f}%  "
            f"{contaminated_count:>10}  {marker}"
        )

    # Show detailed examples
    print("\n" + "=" * 120)
    print("DETAILED EXAMPLES OF CONTAMINATION")
    print("=" * 120)

    for result in results:
        if result["overlap"]["overlap_percentage"] > 5 or result["contaminated_footnotes"]:
            print(f"\n{result['pdf_name']}")
            print("-" * 120)
            print(f"  Footnote chars: {result['footnote_chars']:,}")
            print(f"  Overlap: {result['overlap']['overlap_percentage']:.1f}%")

            if result["overlap"]["overlapping_chunks"]:
                print("\n  Example overlapping chunks found in body:")
                for chunk in result["overlap"]["overlapping_chunks"][:3]:
                    print(f"    • '{chunk[:80]}...'")

            if result["contaminated_footnotes"]:
                print(
                    f"\n  Complete footnotes found in body ({len(result['contaminated_footnotes'])} cases):"
                )
                for fn in result["contaminated_footnotes"][:3]:
                    print(f"    [{fn['index']}] '{fn['text']}...'")

    # Check raw HTML patterns
    print("\n" + "=" * 120)
    print("RAW HTML FOOTNOTE MARKER PATTERNS")
    print("=" * 120)

    for result in results[:3]:  # Show first 3 documents
        if "raw_html" in result and result["raw_html"]["found"]:
            print(f"\n{result['pdf_name']}")
            print("-" * 120)

            patterns = result["raw_html"]["sample_patterns"]

            if patterns["footnote_markers"]:
                print("\n  Footnote markers found:")
                for marker in patterns["footnote_markers"][:2]:
                    print(f"    {marker[:100]}...")

            if patterns["sup_tags"]:
                print("\n  Superscript tags found:")
                for tag in patterns["sup_tags"][:2]:
                    print(f"    {tag}")

            if patterns["footnote_refs"]:
                print("\n  Footnote references found:")
                for ref in patterns["footnote_refs"][:2]:
                    print(f"    {ref}")

    # Summary
    print("\n" + "=" * 120)
    print("SUMMARY")
    print("=" * 120)

    high_overlap = [r for r in results if r["overlap"]["overlap_percentage"] > 10]
    some_overlap = [r for r in results if 1 < r["overlap"]["overlap_percentage"] <= 10]
    no_overlap = [r for r in results if r["overlap"]["overlap_percentage"] <= 1]

    print(f"\nDocuments with HIGH footnote contamination (>10%): {len(high_overlap)}")
    for r in high_overlap:
        print(f"  • {r['pdf_name']}: {r['overlap']['overlap_percentage']:.1f}%")

    print(f"\nDocuments with SOME footnote contamination (1-10%): {len(some_overlap)}")
    for r in some_overlap:
        print(f"  • {r['pdf_name']}: {r['overlap']['overlap_percentage']:.1f}%")

    print(f"\nDocuments with NO significant contamination (<1%): {len(no_overlap)}")

    if high_overlap or some_overlap:
        print("\n⚠️  ISSUE DETECTED:")
        print(
            f"   {len(high_overlap) + len(some_overlap)} documents have footnote text in body text"
        )
        print("   This could inflate body text counts and skew coverage metrics")
        print("\n   RECOMMENDATION: Re-parse HTML to properly separate body and footnotes")
    else:
        print("\n✓ No significant footnote contamination detected")


if __name__ == "__main__":
    main()
