#!/usr/bin/env python3
"""
Law Review Article Scraper

Scrapes HTML/PDF pairs from law reviews using pattern configurations.
Uses law_review_patterns.json for base URLs and search endpoints.

Issue: https://github.com/donaldbraman/docling-testing/issues/4
"""

import json
import random
import re
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


class LawReviewScraper:
    """Scrapes HTML/PDF article pairs from law reviews."""

    def __init__(self, patterns_file: Path, output_dir: Path):
        """Initialize scraper with patterns and output directory."""
        self.patterns_file = patterns_file
        self.output_dir = output_dir
        self.html_dir = output_dir / "raw_html"
        self.pdf_dir = output_dir / "raw_pdf"

        # Create output directories
        self.html_dir.mkdir(parents=True, exist_ok=True)
        self.pdf_dir.mkdir(parents=True, exist_ok=True)

        # Load patterns
        with open(patterns_file) as f:
            data = json.load(f)
            self.patterns = data.get("journals", data)  # Handle nested structure

        # Session for requests
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
        )

        # Rate limiting
        self.min_delay = 2.0  # seconds between requests
        self.max_delay = 5.0

        # Statistics
        self.stats = {
            "journals_attempted": 0,
            "journals_succeeded": 0,
            "articles_found": 0,
            "html_downloaded": 0,
            "pdf_downloaded": 0,
            "pairs_complete": 0,
        }

    def _delay(self):
        """Polite delay between requests."""
        time.sleep(random.uniform(self.min_delay, self.max_delay))

    def _fetch_url(self, url: str, stream: bool = False) -> requests.Response | None:
        """Fetch URL with error handling."""
        try:
            response = self.session.get(url, timeout=30, stream=stream)
            response.raise_for_status()
            return response
        except Exception as e:
            print(f"      ✗ Error fetching {url}: {e}")
            return None

    def _sanitize_filename(self, name: str) -> str:
        """Convert name to safe filename."""
        # Replace special characters with underscores
        name = re.sub(r"[^\w\s-]", "", name)
        name = re.sub(r"[-\s]+", "_", name)
        return name[:100]  # Limit length

    def discover_articles_via_search(self, journal_key: str, config: dict) -> list[dict]:
        """Discover articles using search functionality."""
        if "search" not in config or not config["search"].get("enabled"):
            return []

        search_config = config["search"]
        search_url = search_config.get("url")
        query_param = search_config.get("query_param", "q")

        if not search_url:
            return []

        print(f"    Searching via {search_url}...")

        # Try generic search query for recent articles
        search_queries = [
            "footnote",  # Common in legal articles
            "analysis",
            "law",
        ]

        articles = []

        for query in search_queries[:1]:  # Just try first query to avoid overload
            params = {query_param: query}

            self._delay()
            response = self._fetch_url(search_url)

            if not response:
                continue

            soup = BeautifulSoup(response.content, "html.parser")

            # Look for article links
            # Common patterns: <a> with "article", "read", or in article lists
            article_links = []

            # Try finding article containers
            for container in soup.find_all(
                ["article", "div"], class_=re.compile(r"article|post|entry")
            ):
                link = container.find("a", href=True)
                if link:
                    article_links.append(link)

            # Fallback: all links that look like articles
            if not article_links:
                article_links = soup.find_all("a", href=re.compile(r"/(article|post|print)/"))

            for link in article_links[:10]:  # Limit to avoid overload
                href = link.get("href")
                title = link.get_text(strip=True) or "Untitled"

                if not href:
                    continue

                # Make absolute URL
                article_url = urljoin(config["base_url"], href)

                # Skip if we've already found this article
                if any(a["url"] == article_url for a in articles):
                    continue

                articles.append(
                    {
                        "title": title,
                        "url": article_url,
                        "journal": config["name"],
                        "journal_key": journal_key,
                    }
                )

            if articles:
                break  # Found articles, no need to try more queries

        return articles

    def discover_articles_via_browse(self, journal_key: str, config: dict) -> list[dict]:
        """Discover articles by browsing journal homepage/issues."""
        base_url = config["base_url"]

        print(f"    Browsing {base_url}...")

        self._delay()
        response = self._fetch_url(base_url)

        if not response:
            return []

        soup = BeautifulSoup(response.content, "html.parser")
        articles = []

        # Look for article links on homepage
        # Try various selectors
        for selector in [
            'article a[href*="article"]',
            "div.article a",
            'a[href*="/article/"]',
            'a[href*="/print/"]',
            "a.article-link",
        ]:
            links = soup.select(selector)

            for link in links[:10]:  # Limit per selector
                href = link.get("href")
                title = link.get_text(strip=True) or "Untitled"

                if not href:
                    continue

                article_url = urljoin(base_url, href)

                # Skip duplicates
                if any(a["url"] == article_url for a in articles):
                    continue

                articles.append(
                    {
                        "title": title,
                        "url": article_url,
                        "journal": config["name"],
                        "journal_key": journal_key,
                    }
                )

            if articles:
                break  # Found some, don't need to try more selectors

        return articles

    def find_pdf_url(self, html_url: str, soup: BeautifulSoup, config: dict) -> str | None:
        """Find PDF download URL for article."""
        base_url = config["base_url"]
        download_variants = config.get("download_variants", [".pdf", "/pdf", "/download/pdf"])

        # Strategy 1: Look for explicit PDF link
        pdf_links = soup.find_all("a", href=re.compile(r"\.pdf$", re.I))
        if pdf_links:
            return urljoin(html_url, pdf_links[0]["href"])

        # Strategy 2: Look for download buttons/links
        for link in soup.find_all("a", string=re.compile(r"download|pdf", re.I)):
            href = link.get("href")
            if href:
                return urljoin(html_url, href)

        # Strategy 3: Try download variants
        for variant in download_variants:
            if variant.startswith("/"):
                # Path-based variant
                pdf_url = urljoin(html_url, variant)
            else:
                # Extension-based variant
                pdf_url = html_url.rstrip("/") + variant

            # Quick HEAD request to check if PDF exists
            try:
                response = self.session.head(pdf_url, timeout=10)
                if response.status_code == 200:
                    content_type = response.headers.get("content-type", "")
                    if "pdf" in content_type.lower():
                        return pdf_url
            except:
                pass

        return None

    def download_article_pair(self, article: dict) -> tuple[bool, bool]:
        """Download both HTML and PDF versions of article."""
        journal_key = article["journal_key"]
        config = self.patterns[journal_key]

        # Generate filename
        title_slug = self._sanitize_filename(article["title"])
        journal_slug = self._sanitize_filename(journal_key)
        base_filename = f"{journal_slug}_{title_slug}"

        html_path = self.html_dir / f"{base_filename}.html"
        pdf_path = self.pdf_dir / f"{base_filename}.pdf"

        # Skip if both already exist
        if html_path.exists() and pdf_path.exists():
            print(f"      ✓ Already downloaded: {base_filename}")
            self.stats["pairs_complete"] += 1
            return True, True

        html_success = False
        pdf_success = False

        # Download HTML
        if not html_path.exists():
            print(f"      Downloading HTML: {article['title'][:60]}...")
            self._delay()
            response = self._fetch_url(article["url"])

            if response:
                html_path.write_bytes(response.content)
                print(f"        ✓ Saved: {html_path.name}")
                html_success = True
                self.stats["html_downloaded"] += 1

                # Parse HTML to find PDF
                soup = BeautifulSoup(response.content, "html.parser")
            else:
                soup = None
        else:
            print(f"      ✓ HTML exists: {html_path.name}")
            html_success = True
            # Load existing HTML to find PDF
            soup = BeautifulSoup(
                html_path.read_text(encoding="utf-8", errors="ignore"), "html.parser"
            )

        # Download PDF
        if not pdf_path.exists() and soup:
            print("      Searching for PDF...")
            pdf_url = self.find_pdf_url(article["url"], soup, config)

            if pdf_url:
                print(f"      Downloading PDF: {pdf_url}")
                self._delay()
                response = self._fetch_url(pdf_url, stream=True)

                if response:
                    # Verify it's actually a PDF
                    content_type = response.headers.get("content-type", "")
                    if "pdf" in content_type.lower() or pdf_url.endswith(".pdf"):
                        pdf_path.write_bytes(response.content)
                        print(f"        ✓ Saved: {pdf_path.name}")
                        pdf_success = True
                        self.stats["pdf_downloaded"] += 1
                    else:
                        print(f"        ✗ Not a PDF (content-type: {content_type})")
            else:
                print("        ✗ No PDF URL found")
        elif pdf_path.exists():
            print(f"      ✓ PDF exists: {pdf_path.name}")
            pdf_success = True

        # Count complete pairs
        if html_path.exists() and pdf_path.exists():
            self.stats["pairs_complete"] += 1

        return html_success, pdf_success

    def scrape_journal(self, journal_key: str, target_articles: int = 5) -> int:
        """Scrape articles from a single journal."""
        if journal_key not in self.patterns:
            print(f"  ✗ Journal not found: {journal_key}")
            return 0

        config = self.patterns[journal_key]
        print(f"\n{'=' * 80}")
        print(f"Scraping: {config['name']}")
        print(f"{'=' * 80}")

        self.stats["journals_attempted"] += 1

        # Discover articles
        articles = []

        # Try search first
        if config.get("search", {}).get("enabled"):
            articles.extend(self.discover_articles_via_search(journal_key, config))

        # Try browsing if search didn't find enough
        if len(articles) < target_articles:
            articles.extend(self.discover_articles_via_browse(journal_key, config))

        if not articles:
            print("  ✗ No articles discovered")
            return 0

        print(f"  Found {len(articles)} articles")
        self.stats["articles_found"] += len(articles)

        # Download article pairs (limit to target)
        pairs_downloaded = 0
        for article in articles[:target_articles]:
            html_ok, pdf_ok = self.download_article_pair(article)
            if html_ok and pdf_ok:
                pairs_downloaded += 1

        if pairs_downloaded > 0:
            self.stats["journals_succeeded"] += 1

        print(f"  ✓ Downloaded {pairs_downloaded} complete pairs")
        return pairs_downloaded

    def scrape_multiple_journals(
        self,
        journal_keys: list[str] | None = None,
        articles_per_journal: int = 5,
        target_total: int = 30,
    ):
        """Scrape from multiple journals until target reached."""
        print(f"{'=' * 80}")
        print("LAW REVIEW ARTICLE SCRAPER")
        print(f"{'=' * 80}")
        print(f"\nTarget: {target_total} complete HTML/PDF pairs")
        print(f"Articles per journal: {articles_per_journal}")

        # Select journals
        if not journal_keys:
            # Default to major law reviews
            journal_keys = [
                "harvard law review",
                "stanford law review",
                "yale law journal",
                "columbia law review",
                "university of chicago law review",
                "new york university law review",
                "virginia law review",
            ]

        print(f"\nTargeted journals ({len(journal_keys)}):")
        for key in journal_keys:
            if key in self.patterns:
                print(f"  - {self.patterns[key]['name']}")

        # Scrape each journal
        for journal_key in journal_keys:
            if self.stats["pairs_complete"] >= target_total:
                print(f"\n✓ Target reached: {target_total} pairs")
                break

            self.scrape_journal(journal_key, articles_per_journal)

        # Final statistics
        print(f"\n{'=' * 80}")
        print("SCRAPING COMPLETE")
        print(f"{'=' * 80}")
        print("\nStatistics:")
        print(f"  Journals attempted: {self.stats['journals_attempted']}")
        print(f"  Journals succeeded: {self.stats['journals_succeeded']}")
        print(f"  Articles found: {self.stats['articles_found']}")
        print(f"  HTML files: {self.stats['html_downloaded']}")
        print(f"  PDF files: {self.stats['pdf_downloaded']}")
        print(f"  Complete pairs: {self.stats['pairs_complete']}")

        if self.stats["pairs_complete"] >= target_total * 0.7:
            print(f"\n✓ Successfully collected {self.stats['pairs_complete']} pairs!")
            print("  Ready for label transfer: python match_html_pdf.py")
        else:
            print(f"\n⚠️  Only {self.stats['pairs_complete']} pairs collected")
            print("  May need to adjust scraping strategy or add more journals")


def main():
    """Run scraper."""
    base_dir = Path(__file__).parent
    patterns_file = base_dir / "data" / "law_review_patterns.json"
    output_dir = base_dir / "data"

    if not patterns_file.exists():
        print(f"❌ Patterns file not found: {patterns_file}")
        print("   Expected: data/law_review_patterns.json")
        return

    # Initialize scraper
    scraper = LawReviewScraper(patterns_file, output_dir)

    # Expanded journal list: 25 top-tier and mid-tier law reviews
    # Focus on journals likely to have semantic PDF tags
    expanded_journals = [
        # Top tier (most likely to have tagged PDFs)
        "harvard law review",
        "stanford law review",
        "yale law journal",
        "columbia law review",
        "university of chicago law review",
        "new york university law review",
        "virginia law review",
        "duke law journal",
        "cornell law review",
        "michigan law review",
        "university of pennsylvania law review",
        "northwestern university law review",
        "california law review",
        "georgetown law journal",
        "texas law review",
        "ucla law review",
        # Mid-tier (good infrastructure)
        "boston university law review",
        "fordham law review",
        "minnesota law review",
        "vanderbilt law review",
        "washington university law review",
        "emory law journal",
        "boston college law review",
        "arizona law review",
        "florida law review",
    ]

    # Scrape articles
    # Target: 250 pairs from 25 journals (10 each for diversity)
    scraper.scrape_multiple_journals(
        journal_keys=expanded_journals, articles_per_journal=10, target_total=250
    )

    print("\nOutput directories:")
    print(f"  HTML: {scraper.html_dir}")
    print(f"  PDF: {scraper.pdf_dir}")


if __name__ == "__main__":
    main()
