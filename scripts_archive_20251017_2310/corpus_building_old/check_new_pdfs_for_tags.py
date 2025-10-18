#!/usr/bin/env python3
"""
Check newly collected PDFs for semantic structure tags.
"""

import json
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
            "path": str(pdf_path),
        }
    except Exception as e:
        return {
            "file": pdf_path.name,
            "tagged": False,
            "producer": f"ERROR: {e}",
            "creator": "ERROR",
            "pages": 0,
            "path": str(pdf_path),
        }


def main():
    pdf_dir = Path("/Users/donaldbraman/Documents/GitHub/docling-testing/data/raw_pdf")
    pdfs = sorted(pdf_dir.glob("*.pdf"))

    print("=" * 100)
    print(f"CHECKING {len(pdfs)} NEW PDFs FOR SEMANTIC TAGS")
    print("=" * 100)

    tagged_pdfs = []
    untagged_pdfs = []

    print("\nChecking PDFs...")
    for i, pdf in enumerate(pdfs, 1):
        if i % 20 == 0:
            print(f"  Progress: {i}/{len(pdfs)} PDFs checked...")

        result = quick_check_tagged(pdf)

        if result["tagged"]:
            tagged_pdfs.append(result)
        else:
            untagged_pdfs.append(result)

    print("\n" + "=" * 100)
    print("TAGGED PDFs FOUND")
    print("=" * 100)

    if tagged_pdfs:
        print(f"\n✅ EXCELLENT! Found {len(tagged_pdfs)} tagged PDFs:\n")
        for result in tagged_pdfs:
            print(f"✓ {result['file']}")
            print(f"  Producer: {result['producer']}")
            print(f"  Creator: {result['creator']}")
            print(f"  Pages: {result['pages']}")
            print()
    else:
        print("\n❌ No tagged PDFs found in this batch")

    print("=" * 100)
    print("SUMMARY")
    print("=" * 100)
    print(f"\nTotal PDFs checked: {len(pdfs)}")
    print(f"Tagged PDFs: {len(tagged_pdfs)} ({len(tagged_pdfs) / len(pdfs) * 100:.1f}%)")
    print(f"Untagged PDFs: {len(untagged_pdfs)} ({len(untagged_pdfs) / len(pdfs) * 100:.1f}%)")

    if tagged_pdfs:
        print(f"\n✅ SUCCESS! We can extract semantic ground truth from {len(tagged_pdfs)} PDFs!")
        print("   Next step: Run extract_semantic_tags.py on these PDFs")

        # Save tagged PDF list
        output_file = Path("data/tagged_pdfs_new.json")
        with open(output_file, "w") as f:
            json.dump(tagged_pdfs, f, indent=2)
        print(f"\n✓ Tagged PDF list saved: {output_file}")
    else:
        print("\n⚠️  No semantic tags found in new PDFs")
        print("   Will rely on HTML-PDF matching for ground truth")


if __name__ == "__main__":
    main()
