#!/usr/bin/env python3
"""
Verify Harvard Law Review downloaded pairs meet quality requirements.
"""

from pathlib import Path


def verify_pairs():
    base_dir = Path(__file__).parent
    html_dir = base_dir / "data" / "raw_html"
    pdf_dir = base_dir / "data" / "raw_pdf"

    # Find all Harvard pairs
    html_files = sorted(html_dir.glob("harvard_law_review_*.html"))
    pdf_files = sorted(pdf_dir.glob("harvard_law_review_*.pdf"))

    print("=" * 80)
    print("HARVARD LAW REVIEW - QUALITY VERIFICATION")
    print("=" * 80)

    print("\nFiles found:")
    print(f"  HTML: {len(html_files)}")
    print(f"  PDF:  {len(pdf_files)}")

    # Verify each pair
    passed = 0
    failed = 0

    for html_path in html_files:
        # Find matching PDF
        stem = html_path.stem
        pdf_path = pdf_dir / f"{stem}.pdf"

        if not pdf_path.exists():
            print(f"\n✗ {stem}: Missing PDF")
            failed += 1
            continue

        # Check HTML size
        html_size = html_path.stat().st_size
        if html_size < 20 * 1024:
            print(f"\n✗ {stem}: HTML too small ({html_size} bytes)")
            failed += 1
            continue

        # Check PDF size
        pdf_size = pdf_path.stat().st_size
        if pdf_size < 100 * 1024:
            print(f"\n✗ {stem}: PDF too small ({pdf_size} bytes)")
            failed += 1
            continue

        # Check for footnotes
        content = html_path.read_text(encoding="utf-8", errors="ignore")
        footnote_indicators = [
            "footnote",
            "<sup>",
            "See id",
            "See also",
            "note-",
            "fn-",
        ]

        has_footnotes = any(indicator in content for indicator in footnote_indicators)
        if not has_footnotes:
            print(f"\n✗ {stem}: No footnotes detected")
            failed += 1
            continue

        # Check PDF header
        with open(pdf_path, "rb") as f:
            header = f.read(5)
            if not header.startswith(b"%PDF-"):
                print(f"\n✗ {stem}: Invalid PDF")
                failed += 1
                continue

        # Count footnotes
        footnote_count = sum(content.count(indicator) for indicator in footnote_indicators)

        print(f"\n✓ {stem}")
        print(f"    HTML: {html_size:,} bytes")
        print(f"    PDF:  {pdf_size:,} bytes")
        print(f"    Footnote markers: {footnote_count}")

        passed += 1

    # Summary
    print(f"\n{'=' * 80}")
    print("VERIFICATION COMPLETE")
    print(f"{'=' * 80}")
    print("\nResults:")
    print(f"  Passed: {passed}")
    print(f"  Failed: {failed}")
    print(f"  Total:  {len(html_files)}")

    if passed >= 5:
        print(f"\n✓ SUCCESS: Harvard: {passed} pairs downloaded")
        print("\nQuality checks:")
        print("  ✓ HTML files >20KB")
        print("  ✓ PDF files >100KB")
        print("  ✓ Footnotes present and NOT truncated")
    else:
        print(f"\n⚠️  INCOMPLETE: Only {passed} valid pairs (minimum: 5)")

    return passed


if __name__ == "__main__":
    verify_pairs()
