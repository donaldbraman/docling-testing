#!/usr/bin/env python3
"""Inspect PDF internal structure and tagging."""

import json
from pathlib import Path

import pdfplumber
import PyPDF2


def inspect_pdf(pdf_path):
    """Inspect a PDF for internal structure, tags, and metadata."""
    info = {
        "file": pdf_path.name,
        "has_tags": False,
        "has_metadata": False,
        "has_bookmarks": False,
        "metadata": {},
        "structure_elements": 0,
        "semantic_info": [],
        "errors": [],
    }

    try:
        # Try PyPDF2 for structure tree
        with open(pdf_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)

            # Check for metadata
            if reader.metadata:
                info["has_metadata"] = True
                info["metadata"] = {k: str(v)[:100] for k, v in reader.metadata.items()}

            # Check for outline (bookmarks)
            if reader.outline:
                info["has_bookmarks"] = True

            # Check for structure tree (tagged PDF)
            if hasattr(reader, "root_object") and "/StructTreeRoot" in reader.root_object:
                info["has_tags"] = True

    except Exception as e:
        info["errors"].append(f"PyPDF2 error: {str(e)[:100]}")

    try:
        # Try pdfplumber for semantic analysis
        with pdfplumber.open(pdf_path) as pdf:
            info["num_pages"] = len(pdf.pages)

            # Analyze first page for structure
            if pdf.pages:
                page = pdf.pages[0]

                # Check for tables (semantic structure)
                tables = page.extract_tables()
                if tables:
                    info["semantic_info"].append(f"Tables: {len(tables)}")

                # Check for text blocks and their properties
                text = page.extract_text()
                if text:
                    lines = text.split("\n")
                    info["semantic_info"].append(f"Text lines: {len(lines)}")

                # Check for structured content
                if hasattr(page, "deduce_header_footer"):
                    try:
                        hf = page.deduce_header_footer()
                        if hf[0] or hf[1]:
                            info["semantic_info"].append("Header/Footer detected")
                    except Exception:
                        pass

    except Exception as e:
        info["errors"].append(f"pdfplumber error: {str(e)[:100]}")

    return info


def main():
    """Inspect sample of PDFs."""
    pdf_dir = Path("data/raw_pdf")
    pdf_files = sorted(pdf_dir.glob("*.pdf"))

    print(f"Found {len(pdf_files)} PDFs\n")
    print("Inspecting first 20 PDFs for structure...\n")

    results = []
    for i, pdf_path in enumerate(pdf_files[:20]):
        print(f"[{i + 1:2d}] {pdf_path.name[:50]:50s} ... ", end="", flush=True)
        info = inspect_pdf(pdf_path)
        results.append(info)

        status = []
        if info["has_tags"]:
            status.append("TAGS")
        if info["has_metadata"]:
            status.append("META")
        if info["has_bookmarks"]:
            status.append("BOOKMARKS")
        if info["semantic_info"]:
            status.append(f"SEMANTIC({len(info['semantic_info'])})")

        if status:
            print(" | ".join(status))
        else:
            print("NO STRUCTURE")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    tagged = sum(1 for r in results if r["has_tags"])
    with_meta = sum(1 for r in results if r["has_metadata"])
    with_bookmarks = sum(1 for r in results if r["has_bookmarks"])
    with_semantic = sum(1 for r in results if r["semantic_info"])

    print(f"PDFs inspected: {len(results)}")
    print(f"  Tagged PDFs: {tagged} ({100 * tagged / len(results):.0f}%)")
    print(f"  With metadata: {with_meta} ({100 * with_meta / len(results):.0f}%)")
    print(f"  With bookmarks: {with_bookmarks} ({100 * with_bookmarks / len(results):.0f}%)")
    print(f"  With semantic info: {with_semantic} ({100 * with_semantic / len(results):.0f}%)")

    # Save detailed results
    with open("data/processed/pdf_structure_analysis.json", "w") as f:
        json.dump(results, f, indent=2)

    print("\nDetailed results saved to: data/processed/pdf_structure_analysis.json")

    # Show samples with best structure
    print("\n" + "=" * 80)
    print("BEST STRUCTURED PDFs")
    print("=" * 80)

    ranked = sorted(
        results,
        key=lambda r: (r["has_tags"], r["has_metadata"], len(r["semantic_info"])),
        reverse=True,
    )
    for r in ranked[:5]:
        print(f"\n{r['file']}")
        if r["metadata"]:
            print(f"  Metadata: {r['metadata']}")
        if r["semantic_info"]:
            print(f"  Semantic: {', '.join(r['semantic_info'])}")


if __name__ == "__main__":
    main()
