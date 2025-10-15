#!/usr/bin/env python3
"""
Extract semantic structure from tagged PDFs.

Check if tagged PDFs contain:
- Header/footer artifacts
- Semantic tags for different content types
- Potential ground truth for training
"""

from pathlib import Path

from pypdf import PdfReader

TAGGED_PDFS = [
    "Anderson et al. - 2019 - The Effects of Holistic Defense on Criminal Justice Outcomes.pdf",
    "Braman et al. - Prosecutors in the Passing Lane Racial Disparities_ Public Safety_ and Prosecutorial Declinations o.pdf",
    "Crespo - 2018 - The hidden law of plea bargaining.pdf",
    "Hogan - Prosecutorial regimes and homicides in the United States was the differentiating shift at the COVID.pdf",
    "Huq - 2019 - Racial equity in algorithmic criminal justice.pdf",
    "Jackson - 1940 - The federal prosecutor.pdf",
    "Rappaport - 2020 - Some doubts about democratizing criminal justice.pdf",
    "Stimson and Smith - 2020 - _Progressive_ Prosecutors Sabotage the Rule of Law_ Raise Crime Rates_ and Ignore Victims.pdf",
    "Vîlcică et al. - 2025 - Organizational culture and context in progressive prosecutorial reform Lessons from Philadelphia.pdf",
    "Wildeman and Wang - 2017 - Mass incarceration_ public health_ and widening inequality in the USA.pdf",
]


def extract_structure_types(struct_elem, depth=0, max_depth=5):
    """Recursively extract structure types from structure tree."""
    if depth > max_depth:
        return []

    types = []

    try:
        # Get the type of this element
        if "/S" in struct_elem:
            elem_type = str(struct_elem["/S"])
            types.append((depth, elem_type))

        # Recursively process children
        if "/K" in struct_elem:
            children = struct_elem["/K"]

            # Handle single child vs array of children
            if not isinstance(children, list):
                children = [children]

            for child in children:
                if hasattr(child, "get_object"):
                    child_obj = child.get_object()
                    types.extend(extract_structure_types(child_obj, depth + 1, max_depth))

    except Exception:
        pass

    return types


def inspect_tagged_pdf(pdf_path: Path):
    """Deep inspection of tagged PDF structure."""
    print("\n" + "=" * 100)
    print(f"INSPECTING: {pdf_path.name}")
    print("=" * 100)

    try:
        reader = PdfReader(pdf_path)
        catalog = reader.trailer["/Root"]

        if "/StructTreeRoot" not in catalog:
            print("❌ Not a tagged PDF")
            return None

        struct_root = catalog["/StructTreeRoot"]

        print(f"\n✓ Tagged PDF with {len(reader.pages)} pages")

        # Extract structure types
        print("\nExtracting structure tree...")
        struct_types = extract_structure_types(struct_root)

        # Count unique types
        type_counts = {}
        for depth, stype in struct_types:
            type_counts[stype] = type_counts.get(stype, 0) + 1

        print("\nStructure element types found:")
        for stype, count in sorted(type_counts.items()):
            print(f"  {stype:30s} {count:5d} occurrences")

        # Check for header/footer related tags
        header_footer_tags = ["/Header", "/Footer", "/Artifact", "/Pagination"]
        found_tags = [tag for tag in header_footer_tags if tag in type_counts]

        if found_tags:
            print(f"\n✅ FOUND HEADER/FOOTER TAGS: {', '.join(found_tags)}")
        else:
            print("\n⚠️  No explicit header/footer tags found")

        return {
            "file": pdf_path.name,
            "pages": len(reader.pages),
            "struct_types": type_counts,
            "has_header_footer": len(found_tags) > 0,
        }

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return None


def main():
    pdf_dir = Path("/Users/donaldbraman/Documents/GitHub/12-factor-agents/test_corpus/pdfs")

    print("=" * 100)
    print("EXTRACTING SEMANTIC STRUCTURE FROM TAGGED PDFs")
    print("=" * 100)

    results = []
    for pdf_name in TAGGED_PDFS:
        pdf_path = pdf_dir / pdf_name
        result = inspect_tagged_pdf(pdf_path)
        if result:
            results.append(result)

    print("\n" + "=" * 100)
    print("SUMMARY")
    print("=" * 100)

    pdfs_with_hf = sum(1 for r in results if r["has_header_footer"])
    print(f"\nTagged PDFs inspected: {len(results)}")
    print(f"PDFs with header/footer tags: {pdfs_with_hf}")

    if pdfs_with_hf > 0:
        print("\n✅ EXCELLENT! We can extract header/footer ground truth from tagged PDFs!")
        print("   Next step: Extract semantic tags and use as training labels")
    else:
        print("\n⚠️  Tagged PDFs don't contain explicit header/footer semantic tags")
        print("   Structure tags present, but not specifically for headers/footers")
        print("   Recommend: Stick with 3-class approach (body_text, footnote, cover)")


if __name__ == "__main__":
    main()
