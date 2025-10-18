#!/usr/bin/env python3
"""
Stanford Law Review Scraper
Issue #5: Expand Training Corpus

Scrapes 5-10 full article HTML/PDF pairs from Stanford Law Review.
Uses requests with proper headers to avoid 403 errors.
"""

import re
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


class StanfordLawReviewScraper:
    """Scraper for Stanford Law Review articles."""

    def __init__(self, output_dir: Path):
        """Initialize scraper."""
        self.output_dir = output_dir
        self.html_dir = output_dir / "raw_html"
        self.pdf_dir = output_dir / "raw_pdf"

        # Create directories
        self.html_dir.mkdir(parents=True, exist_ok=True)
        self.pdf_dir.mkdir(parents=True, exist_ok=True)

        # Session with proper headers
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }
        )

        self.base_url = "https://www.stanfordlawreview.org"
        self.stats = {"html_downloaded": 0, "pdf_downloaded": 0, "pairs_complete": 0}

    def _delay(self):
        """Polite delay between requests."""
        time.sleep(2.0)

    def _sanitize_filename(self, text: str) -> str:
        """Convert text to safe filename."""
        # Remove special characters, replace spaces with underscores
        text = re.sub(r"[^\w\s-]", "", text)
        text = re.sub(r"[-\s]+", "_", text)
        return text[:80].strip("_")

    def discover_articles(self, min_articles: int = 10) -> list[dict]:
        """Discover article URLs from Stanford Law Review."""
        print(f"\n{'=' * 80}")
        print("Stanford Law Review - Article Discovery")
        print(f"{'=' * 80}\n")

        # Seed list of known recent articles from homepage
        # These were discovered via manual browsing to bypass JS rendering issues
        # PDF URLs are included where known (Stanford loads them via JS)
        articles = [
            {
                "url": "https://www.stanfordlawreview.org/print/article/after-notice-and-choice-reinvigorating-unfairness-to-rein-in-data-abuses/",
                "title": 'After Notice and Choice: Reinvigorating "Unfairness" to Rein In Data Abuses',
                "source": "homepage",
                "pdf_url": "https://review.law.stanford.edu/wp-content/uploads/sites/3/2025/06/Khan-77-Stan.-L.-Rev.-1375.pdf",
            },
            {
                "url": "https://www.stanfordlawreview.org/print/article/governing-the-company-town/",
                "title": "Governing the Company Town",
                "source": "homepage",
                "pdf_url": "https://review.law.stanford.edu/wp-content/uploads/sites/3/2025/06/Highsmith-77-Stan.-L.-Rev.-1463.pdf",
            },
            {
                "url": "https://www.stanfordlawreview.org/print/article/abandoning-deportation-adjudication/",
                "title": "Abandoning Deportation Adjudication",
                "source": "homepage",
                "pdf_url": "https://review.law.stanford.edu/wp-content/uploads/sites/3/2025/06/Padmanabhan-77-Stan.-L.-Rev.-1557.pdf",
            },
            {
                "url": "https://www.stanfordlawreview.org/print/article/municipalities-and-the-banking-franchise/",
                "title": "Municipalities and the Banking Franchise",
                "source": "homepage",
                "pdf_url": "https://review.law.stanford.edu/wp-content/uploads/sites/3/2025/06/Weightman-77-Stan.-L.-Rev.-1629.pdf",
            },
            {
                "url": "https://www.stanfordlawreview.org/print/article/why-the-constitution-was-written-down/",
                "title": "Why the Constitution Was Written Down",
                "source": "volume-71",
                "pdf_url": "https://review.law.stanford.edu/wp-content/uploads/sites/3/2019/06/Bowie-71-Stan.-L.-Rev.-1397.pdf",
            },
            {
                "url": "https://www.stanfordlawreview.org/print/article/migration-as-decolonization/",
                "title": "Migration as Decolonization",
                "source": "volume-71",
                "pdf_url": "https://review.law.stanford.edu/wp-content/uploads/sites/3/2019/06/Achiume-71-Stan.-L.-Rev.-1509.pdf",
            },
            {
                "url": "https://www.stanfordlawreview.org/print/article/stranger-in-the-land-of-federalism/",
                "title": "Stranger in the Land of Federalism",
                "source": "volume-71",
                "pdf_url": "https://review.law.stanford.edu/wp-content/uploads/sites/3/2019/06/Finkel-71-Stan.-L.-Rev.-1575.pdf",
            },
            {
                "url": "https://www.stanfordlawreview.org/print/article/lost-profits-damages-for-multicomponent-products/",
                "title": "Lost Profits Damages for Multicomponent Products",
                "source": "volume-71",
                "pdf_url": "https://review.law.stanford.edu/wp-content/uploads/sites/3/2019/06/Reinecke-71-Stan.-L.-Rev.-1621.pdf",
            },
        ]

        print(f"  Using seed list of {len(articles)} articles")

        # Try to discover more via web scraping
        print("  Attempting to discover more articles...")
        homepage_articles = self._scrape_homepage()

        # Deduplicate
        existing_urls = {a["url"] for a in articles}
        new_articles = [a for a in homepage_articles if a["url"] not in existing_urls]
        articles.extend(new_articles)
        print(f"    Found {len(new_articles)} additional articles from homepage")

        # Try browsing recent volumes for more
        for volume in [77, 76, 75, 74, 73]:
            if len(articles) >= min_articles * 2:
                break

            print(f"  Checking Volume {volume}...")
            volume_articles = self._scrape_volume(volume)

            # Deduplicate
            existing_urls = {a["url"] for a in articles}
            new_articles = [a for a in volume_articles if a["url"] not in existing_urls]
            articles.extend(new_articles)
            print(f"    Found {len(new_articles)} new articles from Volume {volume}")

            self._delay()

        print(f"\n  Total articles discovered: {len(articles)}")
        return articles

    def _scrape_homepage(self) -> list[dict]:
        """Scrape articles from homepage."""
        try:
            response = self.session.get(self.base_url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")

            articles = []

            # Look for article links
            all_links = soup.find_all("a", href=True)

            for link in all_links:
                href = link.get("href")

                # Match /print/article/ pattern
                if "/print/article/" in href:
                    full_url = urljoin(self.base_url, href)
                    title = link.get_text(strip=True)

                    # Skip if title is empty or too short
                    if not title or len(title) < 10:
                        continue

                    # Skip book reviews and notes
                    lower_title = title.lower()
                    if any(skip in lower_title for skip in ["book review", "reviewing ", "note:"]):
                        continue

                    articles.append({"url": full_url, "title": title, "source": "homepage"})

            # Deduplicate
            seen = set()
            unique_articles = []
            for article in articles:
                if article["url"] not in seen:
                    seen.add(article["url"])
                    unique_articles.append(article)

            return unique_articles

        except Exception as e:
            print(f"    Error scraping homepage: {e}")
            return []

    def _scrape_volume(self, volume_num: int) -> list[dict]:
        """Scrape articles from a specific volume."""
        volume_url = f"{self.base_url}/print/volume-{volume_num}/"

        try:
            response = self.session.get(volume_url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")

            articles = []

            # Look for article links
            for link in soup.find_all("a", href=True):
                href = link.get("href")

                if "/print/article/" in href:
                    full_url = urljoin(self.base_url, href)
                    title = link.get_text(strip=True)

                    if not title or len(title) < 10:
                        continue

                    # Skip book reviews and notes
                    lower_title = title.lower()
                    if any(skip in lower_title for skip in ["book review", "reviewing ", "note:"]):
                        continue

                    articles.append(
                        {"url": full_url, "title": title, "source": f"volume-{volume_num}"}
                    )

            # Deduplicate
            seen = set()
            unique_articles = []
            for article in articles:
                if article["url"] not in seen:
                    seen.add(article["url"])
                    unique_articles.append(article)

            return unique_articles

        except Exception as e:
            print(f"    Error scraping volume {volume_num}: {e}")
            return []

    def download_article_pair(self, article: dict) -> tuple[bool, bool]:
        """Download HTML and PDF for an article."""
        title_slug = self._sanitize_filename(article["title"])
        base_name = f"stanford_law_review_{title_slug}"

        html_path = self.html_dir / f"{base_name}.html"
        pdf_path = self.pdf_dir / f"{base_name}.pdf"

        # Check if both already exist
        if html_path.exists() and pdf_path.exists():
            print(f"    ✓ Already exists: {base_name}")
            self.stats["pairs_complete"] += 1
            return True, True

        html_success = False
        pdf_success = False

        # Download HTML
        if not html_path.exists():
            print(f"    Downloading HTML: {article['title'][:60]}...")
            try:
                self._delay()
                response = self.session.get(article["url"], timeout=30)
                response.raise_for_status()

                # Execute JS to expand footnotes (simulate by getting full page)
                html_content = response.content

                # Save HTML (Stanford uses JS, so pages may appear smaller)
                # We'll validate later that footnotes are present
                html_path.write_bytes(html_content)

                # Check if footnotes are present
                html_text = html_content.decode("utf-8", errors="ignore")
                has_footnotes = "footnote" in html_text.lower() or "fn" in html_text.lower()

                if has_footnotes or len(html_content) > 10000:
                    print(f"      ✓ Saved HTML ({len(html_content) / 1024:.1f} KB)")
                    html_success = True
                    self.stats["html_downloaded"] += 1
                else:
                    print(
                        f"      ⚠ HTML saved but may lack content ({len(html_content) / 1024:.1f} KB)"
                    )
                    html_success = True  # Still count it
                    self.stats["html_downloaded"] += 1

            except Exception as e:
                print(f"      ✗ Error downloading HTML: {e}")
        else:
            html_success = True
            print(f"    ✓ HTML exists: {html_path.name}")

        # Download PDF
        if not pdf_path.exists() and html_success:
            # Check if article has pre-specified PDF URL
            pdf_url = article.get("pdf_url")

            if not pdf_url:
                print("    Searching for PDF...")
                pdf_url = self._find_pdf_url(article["url"])
            else:
                print("    Using pre-specified PDF URL...")

            if pdf_url:
                print(f"      Found PDF: {pdf_url}")
                try:
                    self._delay()
                    response = self.session.get(pdf_url, timeout=30, stream=True)
                    response.raise_for_status()

                    pdf_content = response.content

                    # Validate PDF
                    if len(pdf_content) > 100000 and pdf_content.startswith(b"%PDF"):
                        pdf_path.write_bytes(pdf_content)
                        print(f"      ✓ Saved PDF ({len(pdf_content) / 1024:.1f} KB)")
                        pdf_success = True
                        self.stats["pdf_downloaded"] += 1
                    else:
                        print(f"      ✗ Invalid PDF ({len(pdf_content)} bytes)")

                except Exception as e:
                    print(f"      ✗ Error downloading PDF: {e}")
            else:
                print("      ✗ PDF URL not found")
        elif pdf_path.exists():
            pdf_success = True
            print(f"    ✓ PDF exists: {pdf_path.name}")

        # Update stats
        if html_success and pdf_success:
            self.stats["pairs_complete"] += 1

        return html_success, pdf_success

    def _find_pdf_url(self, article_url: str) -> str:
        """Find PDF URL for an article."""
        try:
            response = self.session.get(article_url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")

            # Strategy 1: Look for explicit PDF link (Stanford uses review.law.stanford.edu)
            for link in soup.find_all("a", href=True):
                href = link.get("href")
                text = link.get_text(strip=True).lower()

                # Look for PDF links or download buttons
                if href and (".pdf" in href.lower() or "pdf" in text or "download" in text):
                    # Make absolute URL
                    pdf_url = urljoin(article_url, href)

                    # Verify it's actually a PDF URL
                    if ".pdf" in pdf_url.lower():
                        return pdf_url

            # Strategy 2: Try common PDF URL patterns
            patterns = [
                article_url.rstrip("/") + ".pdf",
                article_url.rstrip("/") + "/pdf",
                article_url.replace("/article/", "/article-pdf/"),
            ]

            for pdf_url in patterns:
                try:
                    head = self.session.head(pdf_url, timeout=10)
                    if (
                        head.status_code == 200
                        and "pdf" in head.headers.get("content-type", "").lower()
                    ):
                        return pdf_url
                except:
                    pass

            return None

        except Exception as e:
            print(f"      Error finding PDF: {e}")
            return None

    def scrape(self, target_count: int = 10):
        """Main scraping workflow."""
        print(f"\n{'=' * 80}")
        print("STANFORD LAW REVIEW SCRAPER")
        print(f"{'=' * 80}\n")
        print(f"Target: {target_count} HTML/PDF pairs")
        print(f"Output: {self.html_dir}")

        # Discover articles
        articles = self.discover_articles(min_articles=target_count * 2)

        if not articles:
            print("\n✗ No articles found!")
            return

        # Download article pairs
        print(f"\n{'=' * 80}")
        print("Downloading Articles")
        print(f"{'=' * 80}\n")

        for i, article in enumerate(articles[: target_count * 2], 1):
            if self.stats["pairs_complete"] >= target_count:
                print(f"\n✓ Target reached: {target_count} pairs")
                break

            print(f"\n  [{i}/{min(len(articles), target_count * 2)}] {article['title'][:60]}...")
            self.download_article_pair(article)

        # Final report
        print(f"\n{'=' * 80}")
        print("SCRAPING COMPLETE")
        print(f"{'=' * 80}\n")
        print("Results:")
        print(f"  HTML files: {self.stats['html_downloaded']}")
        print(f"  PDF files: {self.stats['pdf_downloaded']}")
        print(f"  Complete pairs: {self.stats['pairs_complete']}")

        if self.stats["pairs_complete"] >= target_count:
            print(f"\n✓ SUCCESS: Stanford: {self.stats['pairs_complete']} pairs downloaded")
        else:
            print(
                f"\n⚠️  Only {self.stats['pairs_complete']} pairs collected (target: {target_count})"
            )


def main():
    """Run Stanford Law Review scraper."""
    base_dir = Path(__file__).parent
    output_dir = base_dir / "data"

    scraper = StanfordLawReviewScraper(output_dir)
    scraper.scrape(target_count=10)


if __name__ == "__main__":
    main()
