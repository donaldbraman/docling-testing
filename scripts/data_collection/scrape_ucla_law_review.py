#!/usr/bin/env python3
"""
UCLA Law Review Article Collection Script

Collects HTML-PDF pairs from UCLA Law Review's online repository.
Focus: Law Meets World and Discourse sections (full-text available).

Target: Minimum 10 complete HTML-PDF pairs
"""

import json
import re
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# Configuration
BASE_URL = "https://www.uclalawreview.org"
OUTPUT_HTML = Path("/Users/donaldbraman/Documents/GitHub/docling-testing/data/raw_html")
OUTPUT_PDF = Path("/Users/donaldbraman/Documents/GitHub/docling-testing/data/raw_pdf")
LOG_DIR = Path(
    "/Users/donaldbraman/Documents/GitHub/docling-testing/data/collection_logs/ucla_law_review"
)
DELAY = 2.5  # Seconds between requests
MAX_ARTICLES = 15  # Stretch goal

# Create directories
OUTPUT_HTML.mkdir(parents=True, exist_ok=True)
OUTPUT_PDF.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Progress tracking
progress_file = LOG_DIR / "progress.txt"
collected_urls_file = LOG_DIR / "collected_urls.json"


class UCLALawReviewScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
        )
        self.collected = self.load_collected_urls()
        self.articles_found = []

    def load_collected_urls(self):
        """Load previously collected URLs to avoid duplicates"""
        if collected_urls_file.exists():
            with open(collected_urls_file) as f:
                return json.load(f)
        return []

    def save_collected_urls(self):
        """Save collected URLs"""
        with open(collected_urls_file, "w") as f:
            json.dump(self.collected, f, indent=2)

    def log(self, message):
        """Log message to console and file"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        print(log_message)
        with open(progress_file, "a") as f:
            f.write(log_message + "\n")

    def make_request(self, url):
        """Make HTTP request with rate limiting"""
        try:
            time.sleep(DELAY)
            response = self.session.get(url, timeout=30)

            if response.status_code == 429:
                self.log("Rate limited (429) - waiting 1 hour")
                return None
            elif response.status_code == 403:
                self.log(f"Forbidden (403) for {url}")
                return None
            elif response.status_code != 200:
                self.log(f"HTTP {response.status_code} for {url}")
                return None

            return response
        except Exception as e:
            self.log(f"Request error for {url}: {e}")
            return None

    def create_slug(self, title):
        """Create filesystem-safe slug from title"""
        # Remove special characters, convert to lowercase
        slug = re.sub(r"[^\w\s-]", "", title.lower())
        slug = re.sub(r"[-\s]+", "_", slug)
        return slug[:100]  # Limit length

    def extract_article_links(self, category_url):
        """Extract article links from category page"""
        self.log(f"Fetching category: {category_url}")
        response = self.make_request(category_url)
        if not response:
            return []

        soup = BeautifulSoup(response.content, "html.parser")
        articles = []

        # Find article links (h2 or h3 headings with links)
        for heading in soup.find_all(["h2", "h3"]):
            link = heading.find("a")
            if link and link.get("href"):
                url = link["href"]
                if url.startswith("/"):
                    url = urljoin(BASE_URL, url)

                # Filter out category/tag/author pages
                if "/category/" not in url and "/tag/" not in url and "/author/" not in url:
                    title = heading.get_text(strip=True)
                    articles.append({"title": title, "url": url})

        self.log(f"Found {len(articles)} article links")
        return articles

    def check_pdf_link(self, soup, article_url):
        """Check if page has PDF download link"""
        # Common PDF link patterns
        pdf_patterns = [
            'a[href$=".pdf"]',
            'a[href*="/pdf/"]',
            "a.pdf-download",
            'a[title*="PDF"]',
            'a[title*="Download"]',
        ]

        for pattern in pdf_patterns:
            pdf_link = soup.select_one(pattern)
            if pdf_link:
                pdf_url = pdf_link.get("href")
                if pdf_url:
                    if pdf_url.startswith("/"):
                        pdf_url = urljoin(BASE_URL, pdf_url)
                    return pdf_url

        return None

    def has_full_text(self, soup):
        """Check if page contains full article text (not just abstract)"""
        # Look for article body content
        article_body = soup.find("div", class_=["entry-content", "article-content", "post-content"])

        if article_body:
            # Count paragraphs
            paragraphs = article_body.find_all("p")
            text_length = sum(len(p.get_text(strip=True)) for p in paragraphs)

            # Full article should have substantial text (>5000 chars)
            if text_length > 5000:
                return True, text_length

        return False, 0

    def download_article(self, article_info):
        """Download article HTML and PDF if available"""
        url = article_info["url"]
        title = article_info["title"]

        # Skip if already collected
        if url in self.collected:
            self.log(f"Skipping (already collected): {title}")
            return False

        self.log(f"Processing: {title}")

        # Fetch article page
        response = self.make_request(url)
        if not response:
            return False

        soup = BeautifulSoup(response.content, "html.parser")

        # Check if full text is available
        has_full, text_length = self.has_full_text(soup)
        if not has_full:
            self.log(f"  ⚠ No full text (only {text_length} chars) - skipping")
            return False

        self.log(f"  ✓ Full text found (~{text_length} chars)")

        # Create filename slug
        slug = self.create_slug(title)
        html_filename = OUTPUT_HTML / f"ucla_law_review_{slug}.html"

        # Save HTML
        with open(html_filename, "w", encoding="utf-8") as f:
            f.write(response.text)
        self.log(f"  ✓ Saved HTML: {html_filename.name}")

        # Check for PDF
        pdf_url = self.check_pdf_link(soup, url)
        pdf_filename = None

        if pdf_url:
            self.log(f"  → PDF link found: {pdf_url}")
            pdf_response = self.make_request(pdf_url)

            if pdf_response and pdf_response.headers.get("content-type", "").startswith(
                "application/pdf"
            ):
                pdf_filename = OUTPUT_PDF / f"ucla_law_review_{slug}.pdf"
                with open(pdf_filename, "wb") as f:
                    f.write(pdf_response.content)
                self.log(f"  ✓ Saved PDF: {pdf_filename.name}")
            else:
                self.log("  ⚠ PDF download failed or not valid PDF")
        else:
            self.log("  ⚠ No PDF link found")

        # Record collection
        self.collected.append(url)
        self.save_collected_urls()

        self.articles_found.append(
            {
                "title": title,
                "url": url,
                "html_file": str(html_filename),
                "pdf_file": str(pdf_filename) if pdf_filename else None,
                "text_length": text_length,
                "collected_at": datetime.now().isoformat(),
            }
        )

        return True

    def collect_from_category(self, category_url, category_name):
        """Collect articles from a category"""
        self.log(f"\n=== Collecting from {category_name} ===")

        # Get article links
        articles = self.extract_article_links(category_url)

        # Download articles
        collected_count = 0
        for article in articles:
            if len(self.articles_found) >= MAX_ARTICLES:
                self.log(f"Reached maximum ({MAX_ARTICLES} articles) - stopping")
                break

            if self.download_article(article):
                collected_count += 1

        self.log(f"Collected {collected_count} articles from {category_name}")
        return collected_count

    def run(self):
        """Main collection process"""
        self.log("=== UCLA Law Review Collection Started ===")
        self.log(f"Target: Minimum 10 articles (stretch: {MAX_ARTICLES})")

        # Categories to collect from (full-text content)
        categories = [
            ("https://www.uclalawreview.org/category/law-meets-world/", "Law Meets World"),
            ("https://www.uclalawreview.org/category/discourse/", "Discourse"),
            ("https://www.uclalawreview.org/category/dialectic/", "Dialectic"),
        ]

        for category_url, category_name in categories:
            if len(self.articles_found) >= MAX_ARTICLES:
                break

            self.collect_from_category(category_url, category_name)

        # Final report
        self.log("\n=== Collection Complete ===")
        self.log(f"Total articles collected: {len(self.articles_found)}")
        self.log(f"Articles with PDFs: {sum(1 for a in self.articles_found if a['pdf_file'])}")
        self.log(f"HTML-only articles: {sum(1 for a in self.articles_found if not a['pdf_file'])}")

        # Save detailed manifest
        manifest_file = LOG_DIR / "collection_manifest.json"
        with open(manifest_file, "w") as f:
            json.dump(
                {
                    "collection_date": datetime.now().isoformat(),
                    "total_collected": len(self.articles_found),
                    "articles": self.articles_found,
                },
                f,
                indent=2,
            )

        self.log(f"Manifest saved to: {manifest_file}")

        # Success check
        if len(self.articles_found) >= 10:
            self.log("✓ SUCCESS: Met minimum requirement (10+ articles)")
        else:
            self.log(f"⚠ WARNING: Only collected {len(self.articles_found)} articles (need 10)")


if __name__ == "__main__":
    scraper = UCLALawReviewScraper()
    scraper.run()
