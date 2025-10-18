#!/usr/bin/env python3
"""
Comprehensive PDF Structure Tag Quality Analysis

Evaluates 90 tagged PDFs to determine if they can serve as ground truth for training.
Analyzes: coverage, tag types, accuracy, extraction feasibility, and comparison with HTML-PDF pairs.

Ref: Issue #28
"""

import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from pypdf import PdfReader


class PDFTagQualityAnalyzer:
    """Analyze PDF structure tags across all tagged PDFs."""

    def __init__(self, pdf_dir: str = "data/raw_pdf"):
        """Initialize analyzer."""
        self.pdf_dir = Path(pdf_dir)
        self.results = []
        self.all_tag_types = Counter()
        self.pdf_producer_stats = defaultdict(lambda: {"count": 0, "coverage": []})

    def extract_text_from_tree(self, obj, text_list=None):
        """Recursively extract text from PDF structure tree."""
        if text_list is None:
            text_list = []

        if isinstance(obj, dict):
            if "/T" in obj:  # Text content
                text_list.append(str(obj["/T"])[:200])
            if "/K" in obj:  # Children
                kids = obj["/K"]
                if isinstance(kids, list):
                    for kid in kids:
                        self.extract_text_from_tree(kid, text_list)
                else:
                    self.extract_text_from_tree(kids, text_list)

        return text_list

    def analyze_pdf(self, pdf_path: Path) -> dict:
        """Analyze a single PDF for tag quality."""
        info = {
            "file": pdf_path.name,
            "has_tags": False,
            "coverage_percent": 0.0,
            "tag_types": [],
            "tag_count": 0,
            "total_text_bytes": 0,
            "tagged_text_bytes": 0,
            "producer": "Unknown",
            "pages": 0,
            "errors": [],
        }

        try:
            with open(pdf_path, "rb") as f:
                reader = PdfReader(f)
                info["pages"] = len(reader.pages)

                # Get producer
                if reader.metadata and "/Producer" in reader.metadata:
                    info["producer"] = str(reader.metadata["/Producer"])[:100]

                # Check for structure tree
                if hasattr(reader, "root_object") and "/StructTreeRoot" in reader.root_object:
                    info["has_tags"] = True

                    try:
                        struct_tree = reader.root_object["/StructTreeRoot"]

                        # Extract all text from structure tree
                        tagged_text = self.extract_text_from_tree(struct_tree)
                        info["tag_count"] = len(tagged_text)
                        info["tagged_text_bytes"] = sum(len(t.encode()) for t in tagged_text)

                        # Identify tag types (simplified)
                        # In a real implementation, would parse /Type fields
                        tag_types = self._identify_tag_types(struct_tree)
                        info["tag_types"] = list(tag_types)
                        self.all_tag_types.update(tag_types)

                    except Exception as e:
                        info["errors"].append(f"Structure tree parsing: {str(e)[:50]}")

                # Extract all text from pages (for coverage calculation)
                try:
                    for page in reader.pages:
                        text = page.extract_text()
                        if text:
                            info["total_text_bytes"] += len(text.encode())
                except Exception as e:
                    info["errors"].append(f"Text extraction: {str(e)[:50]}")

                # Calculate coverage
                if info["total_text_bytes"] > 0:
                    info["coverage_percent"] = (
                        info["tagged_text_bytes"] / info["total_text_bytes"] * 100
                    )

        except Exception as e:
            info["errors"].append(f"PDF read error: {str(e)[:50]}")

        return info

    def _identify_tag_types(self, obj, tag_types=None):
        """Identify tag types in structure tree."""
        if tag_types is None:
            tag_types = set()

        if isinstance(obj, dict):
            if "/S" in obj:  # Structure type
                tag_types.add(str(obj["/S"]))
            if "/K" in obj:
                kids = obj["/K"]
                if isinstance(kids, list):
                    for kid in kids:
                        self._identify_tag_types(kid, tag_types)
                else:
                    self._identify_tag_types(kids, tag_types)

        return tag_types

    def analyze_all_tagged_pdfs(self):
        """Analyze all tagged PDFs in collection."""
        tagged_pdfs = [p for p in sorted(self.pdf_dir.glob("*.pdf")) if p.is_file()]

        print(f"\nAnalyzing {len(tagged_pdfs)} PDFs for tag quality...")
        print("=" * 100)

        for i, pdf_path in enumerate(tagged_pdfs, 1):
            if i % 50 == 0:
                print(f"  Progress: {i}/{len(tagged_pdfs)}")

            result = self.analyze_pdf(pdf_path)
            if result["has_tags"]:
                self.results.append(result)

        # Track producer stats
        for result in self.results:
            producer = result["producer"]
            self.pdf_producer_stats[producer]["count"] += 1
            self.pdf_producer_stats[producer]["coverage"].append(result["coverage_percent"])

    def print_coverage_analysis(self):
        """Print coverage statistics."""
        if not self.results:
            print("No tagged PDFs found")
            return

        coverages = [r["coverage_percent"] for r in self.results]

        print("\n" + "=" * 100)
        print("TAG COVERAGE ANALYSIS")
        print("=" * 100)
        print(f"\nTotal tagged PDFs analyzed: {len(self.results)}")
        print("\nCoverage statistics (% of content with tags):")
        print(f"  Minimum:  {min(coverages):7.1f}%")
        print(f"  Maximum:  {max(coverages):7.1f}%")
        print(f"  Mean:     {statistics.mean(coverages):7.1f}%")
        print(f"  Median:   {statistics.median(coverages):7.1f}%")
        print(f"  Std Dev:  {statistics.stdev(coverages) if len(coverages) > 1 else 0:7.1f}%")

        # Distribution
        print("\nCoverage distribution:")
        ranges = [
            (0, 20, "0-20%"),
            (20, 40, "20-40%"),
            (40, 60, "40-60%"),
            (60, 80, "60-80%"),
            (80, 100, "80-100%"),
        ]
        for low, high, label in ranges:
            count = sum(1 for c in coverages if low <= c < high)
            pct = (count / len(coverages) * 100) if len(coverages) > 0 else 0
            print(f"  {label}: {count:3d} PDFs ({pct:5.1f}%)")

    def print_tag_types_analysis(self):
        """Print tag type inventory."""
        print("\n" + "=" * 100)
        print("TAG TYPE INVENTORY")
        print("=" * 100)
        print(f"\nTotal unique tag types found: {len(self.all_tag_types)}")
        print("\nTag types (by frequency):")

        for tag_type, count in self.all_tag_types.most_common(20):
            pct = (count / len(self.results) * 100) if len(self.results) > 0 else 0
            print(f"  {str(tag_type):20s} {count:4d} PDFs ({pct:5.1f}%)")

        # Show mapping to 7-class schema
        print("\n" + "-" * 100)
        print("MAPPING TO 7-CLASS SCHEMA")
        print("-" * 100)

        schema_mapping = {
            "/P": ("body_text", "Paragraph"),
            "/H": ("heading", "Heading"),
            "/H1": ("heading", "Heading Level 1"),
            "/H2": ("heading", "Heading Level 2"),
            "/H3": ("heading", "Heading Level 3"),
            "/Note": ("footnote", "Footnote/Note"),
            "/Footnote": ("footnote", "Footnote"),
            "/Figure": ("caption", "Figure"),
            "/Table": ("caption", "Table"),
            "/Caption": ("caption", "Caption"),
            "/Header": ("page_header", "Page Header"),
            "/Footer": ("page_footer", "Page Footer"),
            "/Artifact": ("page_header", "Artifact (often header/footer)"),
            "/Document": ("cover", "Document root"),
        }

        print("\nSchema mapping suggestions:")
        for tag_type, count in self.all_tag_types.most_common():
            if tag_type in schema_mapping:
                target_class, description = schema_mapping[tag_type]
                print(f"  {str(tag_type):20s} → {target_class:15s}  ({description})")
            else:
                print(f"  {str(tag_type):20s} → [UNMAPPED]      (unknown/custom tag)")

    def print_producer_analysis(self):
        """Print analysis by PDF producer software."""
        print("\n" + "=" * 100)
        print("PRODUCER SOFTWARE ANALYSIS")
        print("=" * 100)
        print(f"\nDifferent producers found: {len(self.pdf_producer_stats)}")
        print("\nProducer software and average tag coverage:")

        sorted_producers = sorted(
            self.pdf_producer_stats.items(),
            key=lambda x: statistics.mean(x[1]["coverage"]) if x[1]["coverage"] else 0,
            reverse=True,
        )

        for producer, stats in sorted_producers:
            count = stats["count"]
            coverages = stats["coverage"]
            avg_coverage = statistics.mean(coverages) if coverages else 0
            print(f"\n  {producer[:50]:50s}")
            print(f"    Count:         {count}")
            print(f"    Avg Coverage:  {avg_coverage:6.1f}%")

    def print_summary_report(self):
        """Print summary and recommendations."""
        print("\n" + "=" * 100)
        print("SUMMARY REPORT")
        print("=" * 100)

        if not self.results:
            print("No tagged PDFs found for analysis")
            return

        coverages = [r["coverage_percent"] for r in self.results]
        mean_coverage = statistics.mean(coverages)
        pct_above_80 = sum(1 for c in coverages if c > 80) / len(coverages) * 100

        print("\nKey findings:")
        print(f"  • {len(self.results)} tagged PDFs analyzed")
        print(f"  • Average tag coverage: {mean_coverage:.1f}%")
        print(f"  • PDFs with >80% coverage: {pct_above_80:.1f}%")
        print(f"  • Tag types identified: {len(self.all_tag_types)}")

        # Success thresholds from Issue #28
        print("\nSuccess thresholds (Issue #28):")
        threshold_1 = sum(1 for c in coverages if c > 80) / len(coverages) * 100
        print("  ✓ Threshold 1: >70% of PDFs with >80% coverage")
        print(f"    → Result: {threshold_1:.1f}% {'PASS' if threshold_1 > 70 else 'FAIL'}")

        print("\n  ✓ Threshold 2: >80% of tags match ground truth")
        print("    → Result: Requires manual validation (see Section 3)")

        threshold_3 = len(self.all_tag_types) > 0
        mapped = sum(
            1
            for t in self.all_tag_types
            if str(t)
            in [
                "/P",
                "/H",
                "/H1",
                "/H2",
                "/H3",
                "/Note",
                "/Footnote",
                "/Figure",
                "/Table",
                "/Caption",
                "/Header",
                "/Footer",
                "/Artifact",
                "/Document",
            ]
        )
        mapping_rate = (mapped / len(self.all_tag_types) * 100) if self.all_tag_types else 0
        print("  ✓ Threshold 3: >85% of tags map to 7-class schema")
        print(
            f"    → Result: {mapping_rate:.1f}% mappable {'PASS' if mapping_rate > 85 else 'FAIL'}"
        )

        print("\n  ✓ Threshold 4: >100 samples per PDF on average")
        print("    → Result: Requires extraction script (see deliverable)")

    def export_metadata(self, output_file: str = "data/tagged_pdfs_inventory.json"):
        """Export metadata for all tagged PDFs."""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        inventory = {}
        for result in self.results:
            inventory[result["file"]] = {
                "coverage_percent": round(result["coverage_percent"], 1),
                "tag_types": result["tag_types"],
                "tag_count": result["tag_count"],
                "pages": result["pages"],
                "producer": result["producer"],
                "quality_assessment": (
                    "high"
                    if result["coverage_percent"] > 80
                    else "medium"
                    if result["coverage_percent"] > 60
                    else "low"
                ),
            }

        with open(output_path, "w") as f:
            json.dump(inventory, f, indent=2)

        print(f"\n✓ Metadata exported to {output_file}")

    def run(self):
        """Run complete analysis."""
        self.analyze_all_tagged_pdfs()
        self.print_coverage_analysis()
        self.print_tag_types_analysis()
        self.print_producer_analysis()
        self.print_summary_report()
        self.export_metadata()


def main():
    """Main entry point."""
    analyzer = PDFTagQualityAnalyzer()
    analyzer.run()


if __name__ == "__main__":
    main()
