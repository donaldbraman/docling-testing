#!/usr/bin/env python3
"""
Batch inspect PDFs to check for tagged structure.
"""

from pathlib import Path

from pypdf import PdfReader


def quick_check_tagged(pdf_path: Path) -> dict:
    """Quick check if PDF is tagged."""
    try:
        reader = PdfReader(pdf_path)
        catalog = reader.trailer["/Root"]

        has_struct = "/StructTreeRoot" in catalog
        producer = reader.metadata.get("/Producer", "Unknown") if reader.metadata else "No metadata"
        creator = reader.metadata.get("/Creator", "Unknown") if reader.metadata else "No metadata"

        return {
            "file": pdf_path.name,
            "tagged": has_struct,
            "producer": str(producer)[:50],
            "creator": str(creator)[:50],
            "pages": len(reader.pages),
        }
    except Exception as e:
        return {
            "file": pdf_path.name,
            "tagged": False,
            "producer": f"ERROR: {e}",
            "creator": "ERROR",
            "pages": 0,
        }


def main():
    pdf_dir = Path("/Users/donaldbraman/Documents/GitHub/12-factor-agents/test_corpus/pdfs")
    pdfs = sorted(pdf_dir.glob("*.pdf"))

    print("=" * 100)
    print(f"CHECKING {len(pdfs)} PDFs FOR TAGGED STRUCTURE")
    print("=" * 100)

    tagged_count = 0
    untagged_count = 0

    results = []
    for pdf in pdfs:
        result = quick_check_tagged(pdf)
        results.append(result)

        if result["tagged"]:
            tagged_count += 1
            status = "✓ TAGGED"
        else:
            untagged_count += 1
            status = "✗ UNTAGGED"

        print(f"\n{status}: {result['file']}")
        print(f"  Producer: {result['producer']}")
        print(f"  Creator: {result['creator']}")
        print(f"  Pages: {result['pages']}")

    print("\n" + "=" * 100)
    print("SUMMARY")
    print("=" * 100)
    print(f"Total PDFs: {len(pdfs)}")
    print(f"Tagged PDFs: {tagged_count} ({tagged_count / len(pdfs) * 100:.1f}%)")
    print(f"Untagged PDFs: {untagged_count} ({untagged_count / len(pdfs) * 100:.1f}%)")

    if tagged_count > 0:
        print("\n✓ GOOD NEWS: Some PDFs have semantic structure!")
        print("  We can extract headers/footers as ground truth from tagged PDFs")
    else:
        print("\n✗ NO TAGGED PDFs: Headers/footers must be inferred from layout")
        print("  Proceed with 3-class approach (body_text, footnote, cover only)")


if __name__ == "__main__":
    main()
