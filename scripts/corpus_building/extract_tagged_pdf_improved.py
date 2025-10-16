#!/usr/bin/env python3
"""
Improved PDF Tag Extraction with Structure Reconstruction

Handles PDFs where structure tree contains hierarchy but no direct text.
Reconstructs mapping by: extract text → map to structure elements → infer semantic labels.

Ref: Issue #28 - Extraction feasibility analysis
"""

import json
from collections import defaultdict
from pathlib import Path

from pypdf import PdfReader


class ImprovedPDFTagExtractor:
    """Extract and reconstruct tagged content from PDFs with structure trees."""

    # Mapping structure tags to semantic classes
    STRUCTURE_TO_CLASS = {
        "/Document": "cover",  # Document root often contains title/cover
        "/Part": "section",  # Major document part
        "/Sect": "section",  # Section (subsection)
        "/H": "heading",
        "/H1": "heading",
        "/H2": "heading",
        "/H3": "heading",
        "/H4": "heading",
        "/P": "body_text",
        "/L": "body_text",  # List
        "/LI": "body_text",  # List item
        "/Note": "footnote",
        "/Footnote": "footnote",
        "/Figure": "caption",
        "/Table": "caption",
        "/Caption": "caption",
        "/Header": "page_header",
        "/Footer": "page_footer",
        "/Artifact": "page_header",  # Often used for headers/footers
        "/Div": "body_text",  # Generic container
        "/TableRow": "caption",
        "/TableHeader": "caption",
    }

    def __init__(self):
        """Initialize extractor."""
        self.results = defaultdict(lambda: {"success": 0, "failed": 0, "samples": []})

    def extract_structure_hierarchy(self, pdf_path: Path) -> dict:
        """Extract and analyze structure hierarchy from PDF."""
        info = {
            "file": pdf_path.name,
            "has_struct_tree": False,
            "hierarchy_depth": 0,
            "structure_tags": [],
            "estimated_samples": 0,
            "extraction_feasible": False,
            "recommendations": [],
            "error": None,
        }

        try:
            with open(pdf_path, "rb") as f:
                reader = PdfReader(f)

                # Check for structure tree
                if (
                    not hasattr(reader, "root_object")
                    or "/StructTreeRoot" not in reader.root_object
                ):
                    info["error"] = "No structure tree found"
                    return info

                info["has_struct_tree"] = True
                struct_tree = reader.root_object["/StructTreeRoot"]

                # Analyze structure
                depth, tags, sample_count = self._analyze_structure(struct_tree, info)
                info["hierarchy_depth"] = depth
                info["structure_tags"] = list(set(tags))
                info["estimated_samples"] = sample_count

                # Determine if extraction is feasible
                info["extraction_feasible"] = len(info["structure_tags"]) > 0

                # Get page text for reference
                total_pages = len(reader.pages)
                total_text_bytes = 0
                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        total_text_bytes += len(text.encode())

                # Provide recommendations
                if info["hierarchy_depth"] < 2:
                    info["recommendations"].append("Shallow hierarchy - may be mostly structural")
                if sample_count == 0:
                    info["recommendations"].append(
                        "Structure exists but may need text reconstruction from pages"
                    )
                if total_text_bytes > 0:
                    info["recommendations"].append(
                        f"Page text available ({total_text_bytes} bytes) - can reconstruct mapping"
                    )

        except Exception as e:
            info["error"] = str(e)[:100]

        return info

    def _analyze_structure(self, obj, info, depth=0, tags_found=None, sample_count=None):
        """Recursively analyze structure tree."""
        if tags_found is None:
            tags_found = []
        if sample_count is None:
            sample_count = [0]  # Use list to allow modification in nested calls

        max_depth = [depth]

        if isinstance(obj, dict):
            # Get tag type
            if "/S" in obj:
                tag_type = obj["/S"]
                tags_found.append(str(tag_type))

                # Check if this element contains text or children
                if "/T" in obj or "/K" in obj:
                    sample_count[0] += 1

            # Traverse children
            if "/K" in obj:
                kids = obj["/K"]
                if isinstance(kids, list):
                    for kid in kids:
                        _, _, new_depth = self._analyze_structure(
                            kid, info, depth + 1, tags_found, sample_count
                        )
                        max_depth[0] = max(max_depth[0], new_depth)
                else:
                    _, _, new_depth = self._analyze_structure(
                        kids, info, depth + 1, tags_found, sample_count
                    )
                    max_depth[0] = max(max_depth[0], new_depth)

        return max_depth[0], tags_found, sample_count[0]

    def batch_analyze(self, pdf_dir: str = "data/raw_pdf"):
        """Analyze all tagged PDFs for extraction feasibility."""
        pdf_path = Path(pdf_dir)
        tagged_pdfs = []

        # Find all tagged PDFs
        for p in sorted(pdf_path.glob("*.pdf")):
            try:
                with open(p, "rb") as f:
                    reader = PdfReader(f)
                    if hasattr(reader, "root_object") and "/StructTreeRoot" in reader.root_object:
                        tagged_pdfs.append(p)
            except Exception:
                pass

        print("\n📊 IMPROVED PDF TAG EXTRACTION ANALYSIS")
        print("=" * 100)
        print(f"Analyzing {len(tagged_pdfs)} tagged PDFs for extraction feasibility...\n")

        feasible_count = 0
        avg_depth = 0
        all_tags = set()

        results = []
        for i, pdf_path in enumerate(tagged_pdfs, 1):
            if i % 20 == 0:
                print(f"  Progress: {i}/{len(tagged_pdfs)}")

            info = self.extract_structure_hierarchy(pdf_path)
            results.append(info)

            if info["extraction_feasible"]:
                feasible_count += 1
            avg_depth += info["hierarchy_depth"]
            all_tags.update(info["structure_tags"])

        avg_depth = avg_depth / len(tagged_pdfs) if tagged_pdfs else 0

        # Print summary
        print("\n" + "=" * 100)
        print("EXTRACTION FEASIBILITY SUMMARY")
        print("=" * 100)
        print(
            f"\nPDFs with extractable structure: {feasible_count}/{len(tagged_pdfs)} ({feasible_count / len(tagged_pdfs) * 100:.1f}%)"
        )
        print(f"Average hierarchy depth: {avg_depth:.1f} levels")
        print(f"Unique structure tags: {len(all_tags)}")
        print(f"All tags found: {sorted(str(t) for t in all_tags)}")

        # Tag mapping analysis
        print("\n" + "-" * 100)
        print("STRUCTURE-TO-CLASS MAPPING")
        print("-" * 100)
        mapped = 0
        for tag in all_tags:
            if str(tag) in self.STRUCTURE_TO_CLASS:
                target_class = self.STRUCTURE_TO_CLASS[str(tag)]
                print(f"  {str(tag):20s} → {target_class}")
                mapped += 1
            else:
                print(f"  {str(tag):20s} → [UNMAPPED]")

        mapping_rate = (mapped / len(all_tags) * 100) if all_tags else 0
        print(f"\nMapping rate: {mapping_rate:.1f}% ({mapped}/{len(all_tags)})")

        # Recommendations
        print("\n" + "-" * 100)
        print("RECOMMENDATIONS")
        print("-" * 100)

        if mapping_rate >= 70:
            print("✓ Most structure tags map to our schema")
        else:
            print(
                f"⚠ Only {mapping_rate:.0f}% of tags map to our schema - may need custom mappings"
            )

        if feasible_count >= len(tagged_pdfs) * 0.8:
            print("✓ Majority of tagged PDFs have extractable structure")
            print("  → Can proceed with structure-based extraction and text reconstruction")
        else:
            print(
                f"⚠ Only {feasible_count} PDFs have good structure - limited extraction feasibility"
            )

        if avg_depth >= 2:
            print("✓ Average hierarchy depth sufficient for meaningful structure")
        else:
            print("⚠ Shallow hierarchy - structure may not be semantically rich")

        # Export detailed results
        output_file = "data/pdf_extraction_feasibility.json"
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\n✓ Detailed results exported to {output_file}")

        return results

    def print_sample_analysis(self, results: list, num_samples: int = 5):
        """Print sample PDFs with detailed structure info."""
        print("\n" + "=" * 100)
        print("SAMPLE PDF STRUCTURE ANALYSIS")
        print("=" * 100)

        feasible_samples = [r for r in results if r["extraction_feasible"]]
        samples_to_show = feasible_samples[:num_samples]

        for sample in samples_to_show:
            print(f"\n📄 {sample['file']}")
            print(f"   Hierarchy depth: {sample['hierarchy_depth']} levels")
            print(f"   Structure tags: {', '.join(sample['structure_tags'])}")
            print(f"   Estimated blocks: ~{sample['estimated_samples']}")
            if sample["recommendations"]:
                print(f"   Notes: {'; '.join(sample['recommendations'])}")


def main():
    """Run extraction feasibility analysis."""
    extractor = ImprovedPDFTagExtractor()
    results = extractor.batch_analyze()
    extractor.print_sample_analysis(results)


if __name__ == "__main__":
    main()
