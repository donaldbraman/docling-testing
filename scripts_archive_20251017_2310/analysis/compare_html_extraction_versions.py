#!/usr/bin/env python3
"""Compare HTML extraction results between v2 and v3."""

import json
from pathlib import Path


def load_extraction(version: str, basename: str) -> dict:
    """Load extraction results from specified version."""
    path = Path(f"data/labeled_html_{version}/{basename}.json")
    if not path.exists():
        return None

    with open(path) as f:
        return json.load(f)


def compare_extractions():
    """Compare all extractions between v2 and v3."""

    v2_dir = Path("data/labeled_html_v2")
    v3_dir = Path("data/labeled_html_v3")

    v2_files = {f.stem for f in v2_dir.glob("*.json")}
    v3_files = {f.stem for f in v3_dir.glob("*.json")}

    common_files = sorted(v2_files & v3_files)

    print("=" * 80)
    print("COMPARING HTML EXTRACTION: v2 (exclusion) vs v3 (positive inclusion)")
    print("=" * 80)
    print(f"\nFound {len(common_files)} common files\n")

    total_v2_body = 0
    total_v2_fn = 0
    total_v3_body = 0
    total_v3_fn = 0

    differences = []

    for basename in common_files:
        v2 = load_extraction("v2", basename)
        v3 = load_extraction("v3", basename)

        if not v2 or not v3:
            continue

        v2_body = v2["stats"]["body_text"]
        v2_fn = v2["stats"]["footnote_text"]
        v3_body = v3["stats"]["body_text"]
        v3_fn = v3["stats"]["footnote_text"]

        total_v2_body += v2_body
        total_v2_fn += v2_fn
        total_v3_body += v3_body
        total_v3_fn += v3_fn

        # Check for differences
        body_diff = v3_body - v2_body
        fn_diff = v3_fn - v2_fn

        if body_diff != 0 or fn_diff != 0:
            differences.append(
                {
                    "basename": basename,
                    "journal": v3.get("journal", "Unknown"),
                    "v2_body": v2_body,
                    "v3_body": v3_body,
                    "body_diff": body_diff,
                    "v2_fn": v2_fn,
                    "v3_fn": v3_fn,
                    "fn_diff": fn_diff,
                }
            )

    # Show differences
    if differences:
        print("FILES WITH DIFFERENCES:")
        print("-" * 80)
        for diff in differences:
            print(f"\n{diff['basename']}")
            print(f"  Journal: {diff['journal']}")
            print(
                f"  Body text:     v2={diff['v2_body']:>4}  v3={diff['v3_body']:>4}  diff={diff['body_diff']:+4}"
            )
            print(
                f"  Footnote text: v2={diff['v2_fn']:>4}  v3={diff['v3_fn']:>4}  diff={diff['fn_diff']:+4}"
            )
    else:
        print("✅ No differences found - extractions are identical!")

    # Summary
    print(f"\n{'=' * 80}")
    print("SUMMARY")
    print(f"{'=' * 80}")
    print("\nv2 (exclusion filters):")
    print(f"  Body text:     {total_v2_body:>4} paragraphs")
    print(f"  Footnote text: {total_v2_fn:>4} paragraphs")

    print("\nv3 (positive inclusion):")
    print(f"  Body text:     {total_v3_body:>4} paragraphs")
    print(f"  Footnote text: {total_v3_fn:>4} paragraphs")

    print("\nDifferences:")
    print(
        f"  Body text:     {total_v3_body - total_v2_body:+5} paragraphs ({((total_v3_body - total_v2_body) / total_v2_body * 100):+.1f}%)"
    )
    print(
        f"  Footnote text: {total_v3_fn - total_v2_fn:+5} paragraphs ({((total_v3_fn - total_v2_fn) / total_v2_fn * 100 if total_v2_fn else 0):+.1f}%)"
    )


if __name__ == "__main__":
    compare_extractions()
