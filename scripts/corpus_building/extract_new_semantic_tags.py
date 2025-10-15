#!/usr/bin/env python3
"""
Extract semantic structure from newly collected tagged PDFs.
"""

import json
from collections import Counter
from pathlib import Path

from pypdf import PdfReader


def extract_structure_types(struct_elem, depth=0, max_depth=10):
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
    """Extract semantic structure from tagged PDF."""
    try:
        reader = PdfReader(pdf_path)
        catalog = reader.trailer["/Root"]

        if "/StructTreeRoot" not in catalog:
            return None

        struct_root = catalog["/StructTreeRoot"]

        # Extract structure types
        struct_types = extract_structure_types(struct_root)

        # Count unique types
        type_counts = {}
        for depth, stype in struct_types:
            type_counts[stype] = type_counts.get(stype, 0) + 1

        return {
            "file": pdf_path.name,
            "pages": len(reader.pages),
            "struct_types": type_counts,
        }

    except Exception:
        return None


def main():
    """Extract semantic tags from all newly collected tagged PDFs."""

    # Load list of tagged PDFs
    tagged_pdfs_file = Path("data/tagged_pdfs_new.json")
    with open(tagged_pdfs_file) as f:
        tagged_pdfs = json.load(f)

    print("=" * 100)
    print(f"EXTRACTING SEMANTIC STRUCTURE FROM {len(tagged_pdfs)} TAGGED PDFs")
    print("=" * 100)

    results = []
    all_types = Counter()

    for i, pdf_info in enumerate(tagged_pdfs, 1):
        if i % 10 == 0:
            print(f"  Progress: {i}/{len(tagged_pdfs)} PDFs processed...")

        pdf_path = Path(pdf_info["path"])
        result = inspect_tagged_pdf(pdf_path)

        if result:
            results.append(result)
            # Aggregate all structure types
            for stype, count in result["struct_types"].items():
                all_types[stype] += count

    print(f"\n✓ Processed {len(results)} tagged PDFs\n")

    print("=" * 100)
    print("AGGREGATE SEMANTIC STRUCTURE TYPES")
    print("=" * 100)

    print(f"\nFound {len(all_types)} unique structure element types:\n")
    for stype, count in sorted(all_types.items(), key=lambda x: x[1], reverse=True):
        print(f"  {stype:40s} {count:6,} occurrences")

    print("\n" + "=" * 100)
    print("CLASSIFICATION OPPORTUNITIES")
    print("=" * 100)

    # Map semantic tags to our classification categories
    classification_mapping = {
        "body_text": ["/P", "/Text", "/NonStruct", "/Div"],
        "heading": ["/H", "/H1", "/H2", "/H3", "/H4", "/H5", "/H6", "/Title"],
        "footnote": ["/Note", "/FN"],
        "reference": ["/BibEntry", "/Reference"],
        "caption": ["/Caption"],
        "table": ["/Table", "/THead", "/TBody", "/TR", "/TH", "/TD"],
        "page_header": ["/Header", "/Artifact"],
        "page_footer": ["/Footer", "/Artifact"],
    }

    print("\nPotential ground truth labels from semantic tags:\n")

    for label, tag_list in classification_mapping.items():
        matching_tags = [tag for tag in tag_list if tag in all_types]
        total_count = sum(all_types[tag] for tag in matching_tags)

        if total_count > 0:
            print(
                f"✓ {label:15s} {total_count:6,} occurrences from tags: {', '.join(matching_tags)}"
            )
        else:
            print(f"✗ {label:15s}     0 occurrences (no matching tags)")

    # Save detailed results
    output_file = Path("data/semantic_structure_analysis.json")
    output_data = {
        "total_pdfs": len(results),
        "all_types": dict(all_types),
        "per_pdf_results": results,
    }

    with open(output_file, "w") as f:
        json.dump(output_data, f, indent=2)

    print(f"\n✓ Detailed analysis saved: {output_file}")

    print("\n" + "=" * 100)
    print("NEXT STEPS")
    print("=" * 100)
    print("\n1. Extract text from tagged PDF elements")
    print("2. Map semantic tags to our 7-class taxonomy")
    print("3. Build ground truth corpus from semantic tags")
    print("4. Combine with HTML-PDF matched labels")
    print("5. Train classifier on comprehensive clean corpus")


if __name__ == "__main__":
    main()
