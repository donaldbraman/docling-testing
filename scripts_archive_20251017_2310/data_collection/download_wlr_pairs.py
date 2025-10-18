#!/usr/bin/env python3
"""
Download verified Wisconsin Law Review HTML-PDF pairs.

Reads the discovered_articles.json file and downloads both HTML and PDF
for each verified article.
"""

import json
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

RATE_LIMIT_DELAY = 2.5  # seconds between requests
DATA_DIR = Path("/Users/donaldbraman/Documents/GitHub/docling-testing/data")
HTML_DIR = DATA_DIR / "raw_html"
PDF_DIR = DATA_DIR / "raw_pdf"
LOG_DIR = DATA_DIR / "collection_logs" / "wisconsin_law_review"


def sanitize_filename(text):
    """Convert text to safe filename."""
    # Remove/replace unsafe characters
    text = re.sub(r"[^\w\s-]", "", text)
    # Replace spaces and multiple dashes
    text = re.sub(r"[-\s]+", "_", text)
    # Lowercase and limit length
    return text.lower()[:100]


def download_html(url, output_path):
    """Download HTML content of an article."""
    print("  Downloading HTML...")
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    # Save the full HTML
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(response.text)

    # Get word count for verification
    soup = BeautifulSoup(response.content, "html.parser")
    article_body = soup.find("article") or soup.find("div", class_="entry-content")
    if article_body:
        text = article_body.get_text(separator=" ", strip=True)
        word_count = len(text.split())
        print(f"    Saved HTML ({word_count} words): {output_path.name}")
        return word_count
    else:
        print(f"    Saved HTML: {output_path.name}")
        return 0


def download_pdf(url, output_path):
    """Download PDF file."""
    print("  Downloading PDF...")
    response = requests.get(url, timeout=30, stream=True)
    response.raise_for_status()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"    Saved PDF ({size_mb:.2f} MB): {output_path.name}")
    return size_mb


def main():
    print("Wisconsin Law Review - Downloading Verified Pairs")
    print("=" * 60)

    # Load discovered articles
    discovered_file = LOG_DIR / "discovered_articles.json"
    with open(discovered_file) as f:
        data = json.load(f)

    articles = data["articles"]
    print(f"Found {len(articles)} verified pairs to download\n")

    # Track downloads
    successful_downloads = []
    failed_downloads = []

    for i, article in enumerate(articles, 1):
        print(f"[{i}/{len(articles)}] {article['title']}")

        # Create filename slug from title
        slug = sanitize_filename(article["title"])
        html_path = HTML_DIR / f"wisconsin_law_review_{slug}.html"
        pdf_path = PDF_DIR / f"wisconsin_law_review_{slug}.pdf"

        try:
            # Download HTML
            word_count = download_html(article["url"], html_path)

            # Wait before next request
            time.sleep(RATE_LIMIT_DELAY)

            # Download PDF
            pdf_size = download_pdf(article["pdf_url"], pdf_path)

            successful_downloads.append(
                {
                    "title": article["title"],
                    "slug": slug,
                    "html_url": article["url"],
                    "pdf_url": article["pdf_url"],
                    "html_path": str(html_path),
                    "pdf_path": str(pdf_path),
                    "word_count": word_count,
                    "pdf_size_mb": pdf_size,
                }
            )

            print("  ✓ SUCCESS\n")

        except Exception as e:
            print(f"  ✗ FAILED: {e}\n")
            failed_downloads.append({"title": article["title"], "error": str(e)})

        # Rate limiting between articles
        if i < len(articles):
            time.sleep(RATE_LIMIT_DELAY)

    # Save download report
    report = {
        "total_articles": len(articles),
        "successful_downloads": len(successful_downloads),
        "failed_downloads": len(failed_downloads),
        "downloads": successful_downloads,
        "failures": failed_downloads,
    }

    report_file = LOG_DIR / "download_report.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)

    # Save progress.txt
    progress_file = LOG_DIR / "progress.txt"
    with open(progress_file, "w") as f:
        f.write("Wisconsin Law Review Collection Progress\n")
        f.write("=" * 60 + "\n\n")
        f.write("Collection Date: 2025-10-16\n")
        f.write("Base URL: https://wlr.law.wisc.edu/\n\n")
        f.write("SUMMARY:\n")
        f.write(f"  Articles checked: {data['total_checked']}\n")
        f.write(f"  Verified pairs found: {data['verified_pairs']}\n")
        f.write(f"  Successfully downloaded: {len(successful_downloads)}\n")
        f.write(f"  Failed downloads: {len(failed_downloads)}\n\n")

        f.write("DOWNLOADED ARTICLES:\n")
        f.write("-" * 60 + "\n")
        for dl in successful_downloads:
            f.write(f"\n{dl['title']}\n")
            f.write(f"  HTML: {dl['html_path']}\n")
            f.write(f"  PDF: {dl['pdf_path']}\n")
            f.write(f"  Word count: {dl['word_count']}\n")
            f.write(f"  PDF size: {dl['pdf_size_mb']:.2f} MB\n")

        if failed_downloads:
            f.write("\n\nFAILED DOWNLOADS:\n")
            f.write("-" * 60 + "\n")
            for fail in failed_downloads:
                f.write(f"\n{fail['title']}\n")
                f.write(f"  Error: {fail['error']}\n")

    print("=" * 60)
    print("DOWNLOAD SUMMARY:")
    print(f"  Successful: {len(successful_downloads)}")
    print(f"  Failed: {len(failed_downloads)}")
    print("\nReports saved:")
    print(f"  {report_file}")
    print(f"  {progress_file}")

    # Print word count analysis
    if successful_downloads:
        word_counts = [dl["word_count"] for dl in successful_downloads]
        over_5k = sum(1 for wc in word_counts if wc >= 5000)
        print("\nWord Count Analysis:")
        print(f"  Articles with 5k+ words: {over_5k}/{len(successful_downloads)}")
        print(f"  Min words: {min(word_counts)}")
        print(f"  Max words: {max(word_counts)}")
        print(f"  Average words: {sum(word_counts) / len(word_counts):.0f}")


if __name__ == "__main__":
    main()
