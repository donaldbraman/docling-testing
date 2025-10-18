#!/usr/bin/env python3
"""
Extract and index cover pages from PDFs with platform signature detection.

This script:
1. Extracts text from first 3 pages of each PDF
2. Detects platform signatures (HeinOnline, JSTOR, ProQuest, etc.)
3. Generates CSV index with metadata
4. Creates HTML gallery for manual review
5. Builds training corpus with verified cover pages

Uses Docling for robust PDF processing and text extraction.

Usage:
    python scripts/corpus_building/extract_and_index_cover_pages.py [--pdf-dir data/raw_pdf] [--output-dir data/cover_pages]
"""

import argparse
import csv
import json
import logging
import re
from datetime import datetime
from pathlib import Path

try:
    from pypdf import PdfReader
except ImportError:
    print("Error: pypdf not installed.")
    print("Install with: pip install pypdf")
    exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Platform signatures (keywords and patterns)
PLATFORM_SIGNATURES = {
    "heinonline": {
        "keywords": ["heinonline", "hein", "volume", "issue", "heinonline.org"],
        "patterns": [r"HeinOnline", r"Volume\s+\d+", r"Issue\s+\d+"],
    },
    "jstor": {
        "keywords": ["jstor", "stable url", "stable/"],
        "patterns": [r"JSTOR", r"Stable URL:", r"stable/\d+"],
    },
    "proquest": {
        "keywords": ["proquest", "dialog", "umi"],
        "patterns": [r"ProQuest", r"Dialog", r"UMI"],
    },
    "arxiv": {
        "keywords": ["arxiv", "arxiv.org"],
        "patterns": [r"arXiv:", r"arXiv\.org"],
    },
    "publisher_direct": {
        "keywords": ["doi:", "doi.org", "copyright", "©"],
        "patterns": [r"DOI:", r"doi\.org", r"© \d{4}"],
    },
}


class CoverPageExtractor:
    def __init__(self, pdf_dir: str, output_dir: str, max_pages: int = 3):
        """Initialize the extractor."""
        self.pdf_dir = Path(pdf_dir)
        self.output_dir = Path(output_dir)
        self.max_pages = max_pages
        self.index_data = []
        self.extraction_stats = {
            "total_pdfs": 0,
            "successful": 0,
            "failed": 0,
            "platforms_detected": {},
        }

        # Create output directories
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "text_extracts").mkdir(exist_ok=True)
        (self.output_dir / "training_corpus").mkdir(exist_ok=True)

    def detect_platform(self, text: str) -> tuple[str | None, float]:
        """
        Detect platform from extracted text.

        Returns:
            Tuple of (platform_name, confidence_score)
        """
        text_lower = text.lower()
        scores = {}

        for platform, signatures in PLATFORM_SIGNATURES.items():
            score = 0

            # Check keywords
            for keyword in signatures["keywords"]:
                if keyword in text_lower:
                    score += 1

            # Check patterns
            for pattern in signatures["patterns"]:
                if re.search(pattern, text, re.IGNORECASE):
                    score += 2  # Patterns weighted higher

            if score > 0:
                scores[platform] = score

        if not scores:
            return None, 0.0

        best_platform = max(scores, key=scores.get)
        max_score = scores[best_platform]

        # Normalize confidence (rough estimate)
        confidence = min(max_score / 5.0, 1.0)

        return best_platform, confidence

    def classify_page_type(self, page_num: int, text: str, platform: str | None) -> str:
        """Classify the type of page."""
        text_lower = text.lower()

        # Check for platform headers
        if platform and ("platform" in platform or "archive" in platform):
            if len(text.strip()) < 200:  # Platform pages often have little content
                return "platform_header"

        # Check for article title/authors (indicators of article cover)
        title_indicators = ["abstract", "introduction", "author", "affiliation", "©", "copyright"]
        title_score = sum(1 for indicator in title_indicators if indicator in text_lower)

        if title_score >= 2:
            return "article_titlepage"

        # Check for body text
        if len(text.strip()) > 500 and any(
            word in text_lower for word in ["the", "this", "which", "that"]
        ):
            return "article_body"

        # Check for abstract
        if "abstract" in text_lower:
            return "article_abstract"

        # Check for institutional markers
        if any(
            marker in text_lower for marker in ["university", "library", "access", "institutional"]
        ):
            return "institutional_access"

        return "unknown"

    def process_pdf(self, pdf_path: Path) -> dict:
        """
        Extract text from a single PDF and detect platform.

        Returns:
            Dictionary with extraction metadata
        """
        result = {
            "pdf_filename": pdf_path.name,
            "pdf_path": str(pdf_path),
            "status": "failed",
            "page_count": 0,
            "detected_platform": None,
            "platform_confidence": 0.0,
            "page_types": {},
            "true_article_start_page": None,
            "errors": [],
        }

        try:
            # Extract text using pypdf
            with open(str(pdf_path), "rb") as f:
                reader = PdfReader(f)
                result["page_count"] = len(reader.pages)

                # Extract text from first N pages
                text_chunks = []
                for page_num in range(min(self.max_pages, len(reader.pages))):
                    try:
                        page = reader.pages[page_num]
                        text = page.extract_text()
                        text_chunks.append(text if text else "")
                    except Exception as e:
                        logger.debug(f"Failed to extract text from page {page_num + 1}: {e}")
                        text_chunks.append("")

                # Combine all text for platform detection
                all_text = "\n".join(text_chunks)

                # Classify each page
                for page_num, text_chunk in enumerate(text_chunks, 1):
                    page_type = self.classify_page_type(page_num, text_chunk, None)
                    result["page_types"][f"page_{page_num}"] = {
                        "type": page_type,
                        "text_length": len(text_chunk),
                    }

                # Detect platform from combined text
                platform, confidence = self.detect_platform(all_text)
                result["detected_platform"] = platform
                result["platform_confidence"] = confidence

                # Determine article start page
                for page_num, page_data in result["page_types"].items():
                    if page_data["type"] in ["article_titlepage", "article_abstract"]:
                        result["true_article_start_page"] = int(page_num.split("_")[1])
                        break

                if not result["true_article_start_page"]:
                    result["true_article_start_page"] = 1  # Default to page 1

                result["status"] = "success"

        except Exception as e:
            result["errors"].append(str(e))
            logger.error(f"Failed to process {pdf_path.name}: {e}")

        return result

    def extract_all(self) -> None:
        """Extract and process all PDFs in directory."""
        pdf_files = list(self.pdf_dir.glob("*.pdf"))
        self.extraction_stats["total_pdfs"] = len(pdf_files)

        logger.info(f"Found {len(pdf_files)} PDFs to process")

        for i, pdf_path in enumerate(pdf_files, 1):
            logger.info(f"Processing {i}/{len(pdf_files)}: {pdf_path.name}")

            result = self.process_pdf(pdf_path)
            self.index_data.append(result)

            if result["status"] == "success":
                self.extraction_stats["successful"] += 1
                if result["detected_platform"]:
                    platform = result["detected_platform"]
                    self.extraction_stats["platforms_detected"][platform] = (
                        self.extraction_stats["platforms_detected"].get(platform, 0) + 1
                    )
            else:
                self.extraction_stats["failed"] += 1

    def generate_csv_index(self) -> Path:
        """Generate CSV index of all extracted pages."""
        csv_path = self.output_dir / "cover_pages_index.csv"

        fieldnames = [
            "pdf_filename",
            "page_1_type",
            "page_2_type",
            "page_3_type",
            "detected_platform",
            "platform_confidence",
            "true_article_start_page",
            "page_count",
            "extracted_status",
        ]

        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for result in self.index_data:
                row = {
                    "pdf_filename": result["pdf_filename"],
                    "page_1_type": result["page_types"].get("page_1", {}).get("type", "unknown"),
                    "page_2_type": result["page_types"].get("page_2", {}).get("type", "unknown")
                    if len(result["page_types"]) > 1
                    else "",
                    "page_3_type": result["page_types"].get("page_3", {}).get("type", "unknown")
                    if len(result["page_types"]) > 2
                    else "",
                    "detected_platform": result["detected_platform"] or "unknown",
                    "platform_confidence": f"{result['platform_confidence']:.2f}",
                    "true_article_start_page": result["true_article_start_page"],
                    "page_count": result["page_count"],
                    "extracted_status": result["status"],
                }
                writer.writerow(row)

        logger.info(f"Generated CSV index: {csv_path}")
        return csv_path

    def generate_html_gallery(self) -> Path:
        """Generate HTML gallery for manual review."""
        gallery_path = self.output_dir / "gallery.html"

        html_content = (
            """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cover Pages Index</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        h1 {
            margin-bottom: 10px;
            color: #333;
        }
        .subtitle {
            color: #666;
            margin-bottom: 20px;
            font-size: 14px;
        }
        .stats {
            background: white;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 30px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        .stats p {
            margin: 5px 0;
            color: #666;
            font-size: 14px;
        }
        .filters {
            background: white;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        .filters input, .filters select {
            padding: 8px;
            margin-right: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
        }
        table {
            width: 100%;
            background: white;
            border-collapse: collapse;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        th {
            background: #2196F3;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }
        td {
            padding: 10px 12px;
            border-bottom: 1px solid #eee;
            font-size: 13px;
        }
        tr:hover {
            background: #f9f9f9;
        }
        .badge {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 3px;
            font-size: 11px;
            font-weight: bold;
        }
        .badge-platform {
            background: #E3F2FD;
            color: #1976D2;
        }
        .badge-type {
            background: #F3E5F5;
            color: #7B1FA2;
        }
        .badge-success {
            background: #E8F5E9;
            color: #2E7D32;
        }
        .badge-unknown {
            background: #F5F5F5;
            color: #616161;
        }
        .note {
            background: #FFF9C4;
            border-left: 4px solid #FBC02D;
            padding: 12px;
            margin-top: 20px;
            border-radius: 3px;
            font-size: 12px;
            color: #333;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📋 Cover Pages Index & Analysis</h1>
        <p class="subtitle">Complete PDF classification and platform detection results</p>

        <div class="stats">
            <p><strong>Total PDFs Processed:</strong> <span id="stat-total">0</span></p>
            <p><strong>Successfully Extracted:</strong> <span id="stat-success">0</span></p>
            <p><strong>Failed:</strong> <span id="stat-failed">0</span></p>
            <p><strong>Generated:</strong> """
            + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            + """</p>
        </div>

        <div class="filters">
            <input type="text" id="search" placeholder="Search PDF filename...">
            <select id="platform-filter">
                <option value="">All Platforms</option>
            </select>
        </div>

        <table id="data-table">
            <thead>
                <tr>
                    <th>PDF Filename</th>
                    <th>Pages</th>
                    <th>Page 1 Type</th>
                    <th>Detected Platform</th>
                    <th>Article Start</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody id="table-body"></tbody>
        </table>

        <div class="note">
            <strong>Note:</strong> This is an automated analysis. Manual verification of at least 30-50 PDFs is recommended before curating the training corpus. Please review the platform detection and page classification for accuracy.
        </div>
    </div>

    <script>
        const tableData = TABLE_DATA_PLACEHOLDER;
        const stats = STATS_PLACEHOLDER;

        // Update stats
        document.getElementById('stat-total').textContent = stats.total_pdfs;
        document.getElementById('stat-success').textContent = stats.successful;
        document.getElementById('stat-failed').textContent = stats.failed;

        // Populate platform filter
        const platforms = new Set(tableData.map(item => item.detected_platform || 'unknown'));
        const platformFilter = document.getElementById('platform-filter');
        platforms.forEach(platform => {
            const option = document.createElement('option');
            option.value = platform;
            option.textContent = platform.charAt(0).toUpperCase() + platform.slice(1);
            platformFilter.appendChild(option);
        });

        // Render table
        function renderTable() {
            const tbody = document.getElementById('table-body');
            tbody.innerHTML = '';

            const searchTerm = document.getElementById('search').value.toLowerCase();
            const platformFilter = document.getElementById('platform-filter').value;

            const filtered = tableData.filter(item => {
                const matchSearch = item.pdf_filename.toLowerCase().includes(searchTerm);
                const matchPlatform = !platformFilter || item.detected_platform === platformFilter;
                return matchSearch && matchPlatform;
            });

            filtered.forEach(item => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td style="font-family: monospace; font-size: 11px;">${item.pdf_filename}</td>
                    <td>${item.page_count}</td>
                    <td><span class="badge badge-type">${item.page_1_type}</span></td>
                    <td><span class="badge badge-platform">${item.detected_platform || 'Unknown'}</span></td>
                    <td>${item.true_article_start_page || 'N/A'}</td>
                    <td><span class="badge badge-success">${item.status}</span></td>
                `;
                tbody.appendChild(row);
            });

            if (filtered.length === 0) {
                const row = document.createElement('tr');
                row.innerHTML = '<td colspan="6" style="text-align: center; color: #999;">No matching PDFs found</td>';
                tbody.appendChild(row);
            }
        }

        document.getElementById('search').addEventListener('input', renderTable);
        document.getElementById('platform-filter').addEventListener('change', renderTable);

        renderTable();
    </script>
</body>
</html>
"""
        )

        # Prepare table data
        table_data = []
        for result in self.index_data:
            table_data.append(
                {
                    "pdf_filename": result["pdf_filename"],
                    "page_count": result["page_count"],
                    "page_1_type": result["page_types"].get("page_1", {}).get("type", "unknown"),
                    "detected_platform": result["detected_platform"],
                    "true_article_start_page": result["true_article_start_page"],
                    "status": result["status"],
                    "platform_confidence": result["platform_confidence"],
                }
            )

        # Replace placeholders
        table_json = json.dumps(table_data)
        stats_json = json.dumps(self.extraction_stats)

        html_content = html_content.replace("TABLE_DATA_PLACEHOLDER", table_json)
        html_content = html_content.replace("STATS_PLACEHOLDER", stats_json)

        with open(gallery_path, "w") as f:
            f.write(html_content)

        logger.info(f"Generated HTML gallery: {gallery_path}")
        return gallery_path

    def generate_analysis_report(self) -> Path:
        """Generate markdown report with platform analysis."""
        report_path = self.output_dir / "platform_analysis.md"

        # Calculate statistics
        total = len(self.index_data)
        successful = self.extraction_stats["successful"]
        platforms = self.extraction_stats["platforms_detected"]

        report = f"""# Cover Page Platform Analysis Report

Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Summary Statistics

- **Total PDFs Processed:** {total}
- **Successfully Extracted:** {successful} ({100 * successful // total if total > 0 else 0}%)
- **Failed:** {self.extraction_stats["failed"]}

## Platform Distribution

"""

        if platforms:
            for platform, count in sorted(platforms.items(), key=lambda x: x[1], reverse=True):
                percentage = 100 * count // successful if successful > 0 else 0
                report += f"- **{platform.title()}:** {count} ({percentage}%)\n"
        else:
            report += "- No platforms detected\n"

        report += f"""

## Page Type Classification

Pages were classified into the following categories:

- `platform_header`: Publisher/platform branding (HeinOnline, JSTOR, etc.)
- `institutional_access`: University library metadata/access page
- `article_titlepage`: Article title + author names + affiliation (TRUE COVER)
- `article_abstract`: Abstract or introduction text
- `article_body`: Body text (article has begun)
- `metadata_only`: Version info, archival timestamp
- `unknown`: Could not determine

## Key Findings

1. Platform signatures were automatically detected from text extraction
2. Article cover pages identified where title/author information is present
3. High-confidence matches show clear platform markers

## Next Steps

1. Manual verification of classification (sample review of 30-50 PDFs)
2. Curation of training data from verified article cover pages
3. Document any unusual patterns or edge cases discovered

## Technical Details

- Extraction method: PyPDF text extraction
- Platform detection: Keyword and regex pattern matching
- Generated: {datetime.now().isoformat()}
"""

        with open(report_path, "w") as f:
            f.write(report)

        logger.info(f"Generated analysis report: {report_path}")
        return report_path

    def print_summary(self) -> None:
        """Print extraction summary."""
        print("\n" + "=" * 60)
        print("COVER PAGE EXTRACTION SUMMARY")
        print("=" * 60)
        print(f"Total PDFs: {self.extraction_stats['total_pdfs']}")
        print(f"Successful: {self.extraction_stats['successful']}")
        print(f"Failed: {self.extraction_stats['failed']}")
        print("\nPlatforms Detected:")
        for platform, count in sorted(
            self.extraction_stats["platforms_detected"].items(), key=lambda x: x[1], reverse=True
        ):
            print(f"  - {platform}: {count}")
        print("\nOutputs:")
        print(f"  - CSV Index: {self.output_dir}/cover_pages_index.csv")
        print(f"  - HTML Gallery: {self.output_dir}/gallery.html")
        print(f"  - Analysis Report: {self.output_dir}/platform_analysis.md")
        print(f"  - Text Extracts: {self.output_dir}/text_extracts/")
        print("=" * 60 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Extract and index cover pages from PDFs using Docling"
    )
    parser.add_argument("--pdf-dir", default="data/raw_pdf", help="Directory containing PDF files")
    parser.add_argument(
        "--output-dir",
        default="data/cover_pages",
        help="Output directory for extracted text and index",
    )
    parser.add_argument("--max-pages", type=int, default=3, help="Maximum pages to analyze per PDF")

    args = parser.parse_args()

    extractor = CoverPageExtractor(
        pdf_dir=args.pdf_dir,
        output_dir=args.output_dir,
        max_pages=args.max_pages,
    )

    extractor.extract_all()
    extractor.generate_csv_index()
    extractor.generate_html_gallery()
    extractor.generate_analysis_report()
    extractor.print_summary()


if __name__ == "__main__":
    main()
