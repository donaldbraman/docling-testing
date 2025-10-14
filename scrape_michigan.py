#!/usr/bin/env python3
"""
Scrape Michigan Law Review articles - HTML and PDF pairs
"""
import requests
import time
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

# Article data
ARTICLES = [
    {
        "title": "Citizen Shareholders: The State as a Fiduciary in International Investment Law",
        "url": "https://michiganlawreview.org/journal/citizen-shareholders-the-state-as-a-fiduciary-in-international-investment-law/"
    },
    {
        "title": "Good Cause for Goodness' Sake: A New Approach to Notice-and-Comment Rulemaking",
        "url": "https://michiganlawreview.org/journal/good-cause-for-goodness-sake-a-new-approach-to-notice-and-comment-rulemaking/"
    },
    {
        "title": "Tort Law in a World of Scarce Compensatory Resources",
        "url": "https://michiganlawreview.org/journal/tort-law-in-a-world-of-scarce-compensatory-resources/"
    },
    {
        "title": "Spending Clause Standing",
        "url": "https://michiganlawreview.org/journal/spending-clause-standing/"
    },
    {
        "title": "Law Enforcement Privilege",
        "url": "https://michiganlawreview.org/journal/law-enforcement-privilege/"
    }
]

# Paths
HTML_DIR = Path("/Users/donaldbraman/Documents/GitHub/docling-testing/data/raw_html")
PDF_DIR = Path("/Users/donaldbraman/Documents/GitHub/docling-testing/data/raw_pdf")

# Ensure directories exist
HTML_DIR.mkdir(parents=True, exist_ok=True)
PDF_DIR.mkdir(parents=True, exist_ok=True)

def slugify(title):
    """Convert title to filename-safe slug"""
    slug = title.lower()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[-\s]+', '_', slug)
    return slug[:80]  # Limit length

def fetch_article(article_data):
    """Fetch HTML and PDF for an article

    NOTE: The HTML from michiganlawreview.org contains the FULL article text
    with all footnotes embedded in the page. This is better than the repository PDFs
    which are only 6-page preview documents.
    """
    title = article_data["title"]
    url = article_data["url"]
    slug = slugify(title)

    print(f"\n=== Processing: {title} ===")
    print(f"URL: {url}")

    # Filenames
    html_file = HTML_DIR / f"michigan_law_review_{slug}.html"
    pdf_file = PDF_DIR / f"michigan_law_review_{slug}.pdf"

    try:
        # Fetch HTML from journal site (contains full article text!)
        print("Fetching HTML from journal site (full article text)...")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        html_content = response.text

        # Check HTML size and footnotes
        html_size = len(html_content.encode('utf-8'))
        print(f"HTML size: {html_size} bytes ({html_size/1024:.1f} KB)")

        if html_size < 20000:
            print(f"WARNING: HTML too small ({html_size} bytes < 20KB)")
            return False

        # Check for footnotes (Michigan Law Review uses modern-footnotes plugin)
        footnote_patterns = [
            r'<(?:div|section)[^>]*class="[^"]*footnote',
            r'<(?:div|section)[^>]*id="[^"]*footnote',
            r'<sup[^>]*>\s*\d+\s*</sup>',
            r'href="#fn',
            r'class="[^"]*endnote',
            r'modern-footnotes-footnote',  # Michigan Law Review specific
            r'data-mfn='  # Footnote numbering
        ]
        has_footnotes = any(re.search(pattern, html_content, re.I) for pattern in footnote_patterns)

        # Count footnotes
        footnote_count = len(re.findall(r'modern-footnotes-footnote|<sup[^>]*>\s*\d+\s*</sup>', html_content, re.I))

        if not has_footnotes:
            print("WARNING: No footnotes detected in HTML")
        else:
            print(f"Footnotes detected: {footnote_count} references found")

        # Find PDF link
        print("Searching for PDF link...")
        pdf_url = None

        # Common patterns for PDF links - prioritize repository/viewcontent links
        pdf_patterns = [
            r'href="([^"]*repository\.law\.umich\.edu[^"]*viewcontent[^"]*)"',
            r'href="([^"]*viewcontent[^"]*)"',
            r'href="([^"]*download[^"]*)"',
            r'href="([^"]*\.pdf)"',
            r"href='([^']*\.pdf)'",
        ]

        for pattern in pdf_patterns:
            matches = re.findall(pattern, html_content, re.I)
            if matches:
                # Filter out external links (not the article itself)
                for match in matches:
                    # Skip common external domains
                    if any(domain in match for domain in ['worldbank.org', 'ojp.gov', 'justice.gov']):
                        continue
                    pdf_url = match
                    break
                if pdf_url:
                    break

        if not pdf_url:
            # Try looking for download button or link text
            download_match = re.search(r'<a[^>]*href="([^"]*)"[^>]*>.*?(?:download|view\s*pdf).*?</a>', html_content, re.I | re.S)
            if download_match:
                pdf_url = download_match.group(1)

        if pdf_url:
            # Make URL absolute
            pdf_url = urljoin(url, pdf_url)
            print(f"Found PDF URL: {pdf_url}")

            # Fetch PDF
            print("Downloading PDF...")
            pdf_response = requests.get(pdf_url, headers=headers, timeout=60)
            pdf_response.raise_for_status()
            pdf_content = pdf_response.content

            # Validate PDF
            pdf_size = len(pdf_content)
            print(f"PDF size: {pdf_size} bytes ({pdf_size/1024:.1f} KB)")

            if pdf_size < 100000:
                print(f"WARNING: PDF too small ({pdf_size} bytes < 100KB)")
                return False

            # Check PDF magic bytes
            if not pdf_content.startswith(b'%PDF'):
                print("WARNING: Invalid PDF format (missing %PDF header)")
                return False

            # Both files are valid - save them
            print("Saving HTML...")
            html_file.write_text(html_content, encoding='utf-8')

            print("Saving PDF...")
            pdf_file.write_bytes(pdf_content)

            print(f"SUCCESS: Saved HTML ({html_size/1024:.1f} KB) and PDF ({pdf_size/1024:.1f} KB)")
            return True
        else:
            print("ERROR: Could not find PDF link in HTML")
            return False

    except Exception as e:
        print(f"ERROR: {e}")
        # Clean up partial files
        if html_file.exists():
            html_file.unlink()
        if pdf_file.exists():
            pdf_file.unlink()
        return False

def main():
    """Main scraping function"""
    print("=" * 70)
    print("Michigan Law Review Scraper")
    print("=" * 70)

    successful = 0
    failed = 0

    for article in ARTICLES:
        success = fetch_article(article)
        if success:
            successful += 1
        else:
            failed += 1

        # Be polite - delay between requests
        time.sleep(2)

    print("\n" + "=" * 70)
    print(f"SUMMARY: Michigan: {successful} pairs downloaded")
    print(f"Failed: {failed}")
    print("=" * 70)

    return successful

if __name__ == "__main__":
    exit(0 if main() >= 3 else 1)
