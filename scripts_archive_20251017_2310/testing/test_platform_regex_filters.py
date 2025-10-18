#!/usr/bin/env python3
"""
Test Platform Regex Filters

This script tests regex pattern filters on cover page PDFs to identify
platform-added covers (HeinOnline, Annual Review, JSTOR, ProQuest) vs
semantic/article covers.

Usage:
    # Test on all verified covers
    python scripts/testing/test_platform_regex_filters.py

    # Test on specific directory
    python scripts/testing/test_platform_regex_filters.py --pdf-dir data/some_pdfs/

    # Test with verbose output
    python scripts/testing/test_platform_regex_filters.py --verbose

Output:
    - CSV report: data/cover_pages/regex_classification_results.csv
    - JSON report: data/cover_pages/regex_classification_results.json
    - Summary report: data/cover_pages/regex_filter_analysis.md
"""

import argparse
import csv
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from pypdf import PdfReader
except ImportError:
    print("Error: pypdf not installed.")
    print("Install with: pip install pypdf")
    exit(1)

# Import our regex patterns module
import sys

sys.path.insert(0, str(Path(__file__).parent))
from platform_regex_patterns import classify_cover, detect_platform

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class PlatformCoverTester:
    def __init__(self, pdf_dir: Path, output_dir: Path, verbose: bool = False):
        """Initialize the tester."""
        self.pdf_dir = Path(pdf_dir)
        self.output_dir = Path(output_dir)
        self.verbose = verbose
        self.results = []
        self.stats = {
            "total_pdfs": 0,
            "successful": 0,
            "failed": 0,
            "platform_covers": 0,
            "semantic_covers": 0,
            "by_platform": {},
        }

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def extract_first_page_text(self, pdf_path: Path) -> str:
        """Extract text from the first page of a PDF."""
        try:
            with open(pdf_path, "rb") as f:
                reader = PdfReader(f)
                if len(reader.pages) == 0:
                    return ""
                page = reader.pages[0]
                text = page.extract_text()
                return text if text else ""
        except Exception as e:
            logger.error(f"Failed to extract text from {pdf_path.name}: {e}")
            return ""

    def test_single_pdf(self, pdf_path: Path) -> dict[str, Any]:
        """Test platform detection on a single PDF."""
        result = {
            "pdf_filename": pdf_path.name,
            "pdf_path": str(pdf_path),
            "platform_detected": None,
            "confidence": 0.0,
            "classification": "unknown",
            "text_snippet": "",
            "text_length": 0,
            "status": "failed",
            "error": None,
        }

        try:
            # Extract text from first page
            text = self.extract_first_page_text(pdf_path)

            if not text:
                result["error"] = "No text extracted"
                return result

            result["text_length"] = len(text)
            result["text_snippet"] = text[:500].replace("\n", " ").strip()

            # Detect platform
            platform, confidence = detect_platform(text, verbose=self.verbose)

            result["platform_detected"] = platform if platform else "None"
            result["confidence"] = confidence
            result["classification"] = classify_cover(text)
            result["status"] = "success"

            if self.verbose:
                print(f"\n{'=' * 60}")
                print(f"File: {pdf_path.name}")
                print(f"Platform: {result['platform_detected']}")
                print(f"Confidence: {confidence:.2f}")
                print(f"Classification: {result['classification']}")
                print(f"Text snippet: {result['text_snippet'][:100]}...")

        except Exception as e:
            logger.error(f"Error processing {pdf_path.name}: {e}")
            result["error"] = str(e)

        return result

    def test_all_pdfs(self) -> list[dict[str, Any]]:
        """Test platform detection on all PDFs in the directory."""
        pdf_files = sorted(self.pdf_dir.glob("*.pdf"))
        self.stats["total_pdfs"] = len(pdf_files)

        logger.info(f"Testing {len(pdf_files)} PDFs from {self.pdf_dir}")

        for pdf_path in pdf_files:
            result = self.test_single_pdf(pdf_path)
            self.results.append(result)

            # Update statistics
            if result["status"] == "success":
                self.stats["successful"] += 1

                if result["classification"] == "platform_cover":
                    self.stats["platform_covers"] += 1
                    platform = result["platform_detected"]
                    self.stats["by_platform"][platform] = (
                        self.stats["by_platform"].get(platform, 0) + 1
                    )
                elif result["classification"] == "semantic_cover":
                    self.stats["semantic_covers"] += 1
            else:
                self.stats["failed"] += 1

        return self.results

    def save_csv_report(self) -> Path:
        """Save results as CSV."""
        csv_path = self.output_dir / "regex_classification_results.csv"

        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            if not self.results:
                return csv_path

            fieldnames = self.results[0].keys()
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.results)

        logger.info(f"CSV report saved to: {csv_path}")
        return csv_path

    def save_json_report(self) -> Path:
        """Save results as JSON."""
        json_path = self.output_dir / "regex_classification_results.json"

        report_data = {
            "generated": datetime.now().isoformat(),
            "source_directory": str(self.pdf_dir),
            "statistics": self.stats,
            "results": self.results,
        }

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)

        logger.info(f"JSON report saved to: {json_path}")
        return json_path

    def save_summary_report(self) -> Path:
        """Save human-readable summary report."""
        md_path = self.output_dir / "regex_filter_analysis.md"

        with open(md_path, "w", encoding="utf-8") as f:
            f.write("# Platform Regex Filter Analysis\n\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**Source Directory:** `{self.pdf_dir}`\n\n")

            f.write("## Summary Statistics\n\n")
            f.write(f"- **Total PDFs Tested:** {self.stats['total_pdfs']}\n")
            f.write(f"- **Successful:** {self.stats['successful']}\n")
            f.write(f"- **Failed:** {self.stats['failed']}\n")
            f.write(
                f"- **Platform Covers:** {self.stats['platform_covers']} ({self.stats['platform_covers'] / max(self.stats['successful'], 1) * 100:.1f}%)\n"
            )
            f.write(
                f"- **Semantic Covers:** {self.stats['semantic_covers']} ({self.stats['semantic_covers'] / max(self.stats['successful'], 1) * 100:.1f}%)\n\n"
            )

            f.write("## Platform Distribution\n\n")
            if self.stats["by_platform"]:
                for platform, count in sorted(
                    self.stats["by_platform"].items(), key=lambda x: x[1], reverse=True
                ):
                    pct = count / max(self.stats["platform_covers"], 1) * 100
                    f.write(f"- **{platform}:** {count} ({pct:.1f}%)\n")
            else:
                f.write("No platform covers detected.\n")

            f.write("\n## Semantic Covers (No Platform Detected)\n\n")
            semantic_covers = [r for r in self.results if r["classification"] == "semantic_cover"]
            if semantic_covers:
                f.write(f"Found {len(semantic_covers)} semantic covers suitable for training:\n\n")
                for result in semantic_covers[:20]:  # Show first 20
                    f.write(f"- `{result['pdf_filename']}`\n")
                if len(semantic_covers) > 20:
                    f.write(f"\n... and {len(semantic_covers) - 20} more\n")
            else:
                f.write("No semantic covers found (all have platform signatures).\n")

            f.write("\n## Platform Covers (To Be Filtered Out)\n\n")
            platform_covers = [r for r in self.results if r["classification"] == "platform_cover"]
            if platform_covers:
                f.write(f"Found {len(platform_covers)} platform covers to filter:\n\n")
                for platform in sorted({r["platform_detected"] for r in platform_covers}):
                    f.write(f"\n### {platform}\n\n")
                    platform_specific = [
                        r for r in platform_covers if r["platform_detected"] == platform
                    ]
                    for result in platform_specific[:10]:  # Show first 10 per platform
                        f.write(
                            f"- `{result['pdf_filename']}` (confidence: {result['confidence']:.2f})\n"
                        )
                    if len(platform_specific) > 10:
                        f.write(f"\n... and {len(platform_specific) - 10} more\n")
            else:
                f.write("No platform covers detected.\n")

            f.write("\n## Next Steps\n\n")
            f.write("1. **Manual validation:** Review random sample of 20-30 PDFs\n")
            f.write("2. **Refine patterns:** Adjust regex if false positives/negatives found\n")
            f.write(
                "3. **Extract text blocks:** Use Docling on semantic covers to count training samples\n"
            )
            f.write(
                "4. **Assess sufficiency:** Determine if semantic covers provide enough training data\n"
            )

        logger.info(f"Summary report saved to: {md_path}")
        return md_path

    def print_summary(self):
        """Print summary statistics to console."""
        print("\n" + "=" * 60)
        print("PLATFORM REGEX FILTER TEST RESULTS")
        print("=" * 60)
        print(f"\nTotal PDFs: {self.stats['total_pdfs']}")
        print(f"Successful: {self.stats['successful']}")
        print(f"Failed: {self.stats['failed']}")
        print(f"\nPlatform Covers: {self.stats['platform_covers']}")
        print(f"Semantic Covers: {self.stats['semantic_covers']}")

        if self.stats["by_platform"]:
            print("\nPlatform Distribution:")
            for platform, count in sorted(
                self.stats["by_platform"].items(), key=lambda x: x[1], reverse=True
            ):
                print(f"  {platform}: {count}")

        print("\n" + "=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Test platform regex filters on cover page PDFs")
    parser.add_argument(
        "--pdf-dir",
        type=str,
        default="data/cover_pages/verified_covers/source_pdfs_cover_page_only",
        help="Directory containing PDFs to test",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/cover_pages",
        help="Directory for output reports",
    )
    parser.add_argument("--verbose", action="store_true", help="Print detailed output for each PDF")

    args = parser.parse_args()

    # Initialize tester
    tester = PlatformCoverTester(
        pdf_dir=Path(args.pdf_dir),
        output_dir=Path(args.output_dir),
        verbose=args.verbose,
    )

    # Run tests
    tester.test_all_pdfs()

    # Save reports
    tester.save_csv_report()
    tester.save_json_report()
    tester.save_summary_report()

    # Print summary
    tester.print_summary()


if __name__ == "__main__":
    main()
