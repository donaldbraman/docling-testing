#!/usr/bin/env python3
"""Real collection worker - downloads HTML and PDF pairs from article URLs."""

import json
import subprocess
import time
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup


class CollectionWorker:
    """Downloads HTML/PDF pairs from discovered article links."""

    def __init__(self, agent_config: dict):
        """Initialize worker."""
        self.id = agent_config["id"]
        self.journal = agent_config["journal"]
        self.base_url = agent_config["base_url"]
        self.slug = agent_config["slug"]

        self.html_dir = Path("data/raw_html")
        self.pdf_dir = Path("data/raw_pdf")
        self.log_dir = Path("data/collection_logs") / self.slug
        self.log_file = self.log_dir / "download.log"

        self.html_dir.mkdir(parents=True, exist_ok=True)
        self.pdf_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.downloaded = 0
        self.failed = 0
        self.start_time = datetime.now()

    def log(self, msg: str) -> None:
        """Log message."""
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{self.id:2d}] {ts} | {self.journal[:35]:35s} | {msg}"
        print(line)
        with open(self.log_file, "a") as f:
            f.write(line + "\n")

    def sanitize_filename(self, text: str) -> str:
        """Convert text to safe filename."""
        return "".join(c if c.isalnum() or c in "-_" else "_" for c in text)[:50]

    def find_pdf_url(self, html_url: str, html_content: str) -> str:
        """Find PDF URL from HTML."""
        try:
            soup = BeautifulSoup(html_content, "html.parser")

            # Look for common PDF patterns
            patterns = [
                "a[href*='.pdf']",
                "a[data-pdf]",
                "button[class*='download']",
                "a[class*='pdf']",
            ]

            for pattern in patterns:
                elements = soup.select(pattern)
                for elem in elements:
                    href = elem.get("href") or elem.get("data-pdf")
                    if href and ".pdf" in href.lower():
                        if href.startswith("http"):
                            return href
                        elif href.startswith("/"):
                            return self.base_url + href
                        else:
                            return html_url.rsplit("/", 1)[0] + "/" + href

            return None
        except Exception as e:
            self.log(f"PDF search error: {str(e)[:30]}")
            return None

    def download_file(self, url: str, output_path: Path, is_pdf: bool = False) -> bool:
        """Download file with curl."""
        try:
            timeout = "30" if is_pdf else "10"
            cmd = [
                "curl",
                "-s",
                "--max-time",
                timeout,
                "-L",
                "-A",
                "Mozilla/5.0 (DoclingBERT Research)",
                url,
            ]

            result = subprocess.run(cmd, capture_output=True, timeout=45)

            if result.returncode == 0 and len(result.stdout) > (50000 if is_pdf else 10000):
                with open(output_path, "wb") as f:
                    f.write(result.stdout)
                return True

            return False
        except Exception as e:
            self.log(f"Download error: {str(e)[:30]}")
            return False

    def collect_article(self, html_url: str, article_num: int) -> bool:
        """Collect one article (HTML + PDF)."""
        try:
            # Download HTML
            self.log(f"Article {article_num}: Fetching HTML...")
            resp = requests.get(html_url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            html_content = resp.text

            # Parse title from HTML or URL
            soup = BeautifulSoup(html_content, "html.parser")
            title_elem = soup.find("h1") or soup.find("title")
            title = title_elem.text[:50] if title_elem else html_url.split("/")[-1][:50]
            article_slug = self.sanitize_filename(title)

            # Save HTML
            html_path = self.html_dir / f"{self.slug}_{article_slug}.html"
            html_path.write_text(html_content)
            self.log(f"  Saved: {html_path.name} ({len(html_content) // 1024}KB)")

            # Find and download PDF
            pdf_url = self.find_pdf_url(html_url, html_content)
            if not pdf_url:
                self.log("  ⚠️  No PDF link found")
                return False

            self.log(f"  PDF URL: {pdf_url[:60]}")
            pdf_path = self.pdf_dir / f"{self.slug}_{article_slug}.pdf"

            if self.download_file(pdf_url, pdf_path, is_pdf=True):
                size_kb = pdf_path.stat().st_size // 1024
                self.log(f"  ✓ PDF saved ({size_kb}KB)")
                self.downloaded += 1
                time.sleep(3)  # Rate limiting
                return True
            else:
                self.log("  ✗ PDF download failed")
                self.failed += 1
                time.sleep(3)
                return False

        except Exception as e:
            self.log(f"Collection error: {str(e)[:40]}")
            self.failed += 1
            time.sleep(3)
            return False

    def collect(self, num_articles: int = 10) -> dict:
        """Collect articles for this journal."""
        self.log(f"Starting real collection ({num_articles} articles)")

        try:
            # Discover and download articles
            resp = requests.get(self.base_url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(resp.content, "html.parser")
            links = soup.find_all("a", href=True)

            article_urls = []
            for link in links:
                href = link.get("href", "")
                if any(x in href.lower() for x in ["/article", "/vol", "/issue"]):
                    if not href.startswith("http"):
                        href = self.base_url + (href if href.startswith("/") else "/" + href)
                    article_urls.append(href)
                    if len(article_urls) >= num_articles * 2:
                        break

            # Download articles
            for i, url in enumerate(article_urls[:num_articles], 1):
                if self.downloaded >= num_articles:
                    break
                self.collect_article(url, i)

        except Exception as e:
            self.log(f"Collection failed: {str(e)[:40]}")

        elapsed = (datetime.now() - self.start_time).total_seconds()
        self.log(f"Done: {self.downloaded} downloaded, {self.failed} failed ({elapsed:.0f}s)")

        return {
            "id": self.id,
            "journal": self.journal,
            "downloaded": self.downloaded,
            "failed": self.failed,
            "target": 10,
        }


def main():
    """Main."""
    import argparse

    parser = argparse.ArgumentParser(description="Real collection worker")
    parser.add_argument("--batch", choices=["tier1", "tier2", "tier3", "all"], default="tier1")
    parser.add_argument("--journal-id", type=int, help="Specific journal ID")
    args = parser.parse_args()

    with open("scripts/deployment/agent_config.json") as f:
        config = json.load(f)

    agents = config["agents"]

    if args.journal_id:
        agents = [a for a in agents if a["id"] == args.journal_id]
    else:
        tier_map = {"tier1": "tier1", "tier2": "tier2", "tier3": "tier3", "all": None}
        tier = tier_map[args.batch]
        if tier:
            agents = [a for a in agents if a["tier"] == tier]

    print(f"\nDownloading from {len(agents)} journals...\n")

    for agent_config in agents:
        worker = CollectionWorker(agent_config)
        worker.collect(num_articles=10)
        time.sleep(2)

    print("\nCollection complete!\n")


if __name__ == "__main__":
    main()
