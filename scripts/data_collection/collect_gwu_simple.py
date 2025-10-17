#!/usr/bin/env python3
"""Simple GWU Law Review collector using subprocess and curl."""

import re
import subprocess
import time
from pathlib import Path

# Configuration
OUTPUT_HTML = Path("/Users/donaldbraman/Documents/GitHub/docling-testing/data/raw_html")
OUTPUT_PDF = Path("/Users/donaldbraman/Documents/GitHub/docling-testing/data/raw_pdf")
LOG_DIR = Path(
    "/Users/donaldbraman/Documents/GitHub/docling-testing/data/collection_logs/gwu_law_review"
)

OUTPUT_HTML.mkdir(parents=True, exist_ok=True)
OUTPUT_PDF.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Article URLs
ARTICLES = [
    "https://www.gwlr.org/coercive-settlements/",
    "https://www.gwlr.org/criminal-investors/",
    "https://www.gwlr.org/non-universal-response-to-the-universal-injunction-problem/",
    "https://www.gwlr.org/chenery-ii-revisited/",
    "https://www.gwlr.org/chevron-bias/",
    "https://www.gwlr.org/how-chevron-deference-fits-into-article-iii/",
    "https://www.gwlr.org/nondelegation-as-constitutional-symbolism/",
    "https://www.gwlr.org/optimal-ossification/",
    "https://www.gwlr.org/overseeing-agency-enforcement/",
    "https://www.gwlr.org/the-ambiguity-fallacy/",
    "https://www.gwlr.org/the-american-nondelegation-doctrine/",
    "https://www.gwlr.org/the-future-of-deference/",
    "https://www.gwlr.org/the-ordinary-questions-doctrine/",
    "https://www.gwlr.org/the-power-to-vacate-a-rule/",
    "https://www.gwlr.org/delegating-and-regulating-the-presidents-section-232-and-ieepa-trade-powers/",
]

DELAY = 2.5
TARGET = 15


def download_url(url, output_path):
    """Download URL using curl with proper headers."""
    cmd = [
        "curl",
        "-s",
        "-f",
        "-H",
        "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        url,
        "-o",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True)
    return result.returncode == 0


def extract_pdf_url(html_path):
    """Extract PDF URL from HTML file."""
    try:
        with open(html_path, encoding="utf-8", errors="ignore") as f:
            content = f.read()

        # Look for PDF URL
        match = re.search(r'https://www\.gwlr\.org/wp-content/uploads/[^">< ]+\.pdf', content)
        if match:
            return match.group(0)
    except Exception as e:
        print(f"  Error reading HTML: {e}")

    return None


def main():
    print("=" * 70)
    print("GWU Law Review Simple Collection Script")
    print("=" * 70)
    print(f"Target: {TARGET} complete HTML-PDF pairs")
    print()

    successful = 0
    failed = 0
    log_entries = []

    for i, url in enumerate(ARTICLES, 1):
        if successful >= TARGET:
            print(f"\n✓ Reached target of {TARGET} pairs")
            break

        print(f"\n[{i}] {url}")

        # Generate filenames
        slug = url.replace("https://www.gwlr.org/", "").rstrip("/")
        base_name = f"gwu_law_review_{slug}"
        html_path = OUTPUT_HTML / f"{base_name}.html"
        pdf_path = OUTPUT_PDF / f"{base_name}.pdf"

        # Download HTML
        print("  Downloading HTML...")
        if not download_url(url, html_path):
            print("  ✗ Failed to download HTML")
            failed += 1
            log_entries.append(f"✗ {url} (HTML download failed)")
            time.sleep(DELAY)
            continue

        # Check file size
        if html_path.stat().st_size < 5000:
            print("  ✗ HTML too small (error page?)")
            html_path.unlink()
            failed += 1
            log_entries.append(f"✗ {url} (HTML too small)")
            time.sleep(DELAY)
            continue

        # Extract PDF URL
        pdf_url = extract_pdf_url(html_path)
        if not pdf_url:
            print("  ✗ No PDF link found")
            html_path.unlink()
            failed += 1
            log_entries.append(f"✗ {url} (no PDF link)")
            time.sleep(DELAY)
            continue

        print(f"  Found PDF: {pdf_url}")

        # Download PDF
        time.sleep(DELAY)
        print("  Downloading PDF...")
        if not download_url(pdf_url, pdf_path):
            print("  ✗ Failed to download PDF")
            html_path.unlink()
            failed += 1
            log_entries.append(f"✗ {url} (PDF download failed)")
            time.sleep(DELAY)
            continue

        # Verify PDF size
        pdf_size = pdf_path.stat().st_size
        if pdf_size < 10000:
            print("  ✗ PDF too small (error?)")
            html_path.unlink()
            pdf_path.unlink()
            failed += 1
            log_entries.append(f"✗ {url} (PDF too small)")
            time.sleep(DELAY)
            continue

        print(f"  ✓ Success! PDF size: {pdf_size:,} bytes")
        successful += 1
        log_entries.append(f"✓ {url}")

        time.sleep(DELAY)

    # Summary
    print("\n" + "=" * 70)
    print("Collection Complete")
    print("=" * 70)
    print(f"Successful pairs: {successful}")
    print(f"Failed attempts: {failed}")
    if successful + failed > 0:
        print(f"Success rate: {successful / (successful + failed) * 100:.1f}%")

    # Write log
    log_path = LOG_DIR / "progress.txt"
    with open(log_path, "w") as f:
        f.write("GWU Law Review Collection Report\n")
        f.write("=" * 70 + "\n")
        f.write(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Successful pairs: {successful}\n")
        f.write(f"Failed attempts: {failed}\n")
        if successful + failed > 0:
            f.write(f"Success rate: {successful / (successful + failed) * 100:.1f}%\n")
        f.write("\nDetails:\n")
        for entry in log_entries:
            f.write(f"{entry}\n")

    print(f"\nLog saved to: {log_path}")

    if successful >= 10:
        print("\n✓ SUCCESS: Met minimum target of 10 pairs")
        return 0
    else:
        print(f"\n⚠ WARNING: Only {successful} pairs (target: 10)")
        return 1


if __name__ == "__main__":
    exit(main())
