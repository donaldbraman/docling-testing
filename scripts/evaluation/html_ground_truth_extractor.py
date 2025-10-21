"""
Extract ground truth labels from HTML files for evaluation.

Parses HTML to identify body text vs other semantic elements
(headers, footnotes, citations, etc.) using:
1. Semantic HTML5 tags (<article>, <main>, <p> with proper context)
2. CSS class patterns (body, content, article, etc.)
3. Heuristic rules (typical legal document structure)

Output: JSON files with ground truth labels for matching against Docling extractions.
"""

import json
import logging
import re
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class HTMLGroundTruthExtractor:
    """Extract semantic ground truth from HTML legal documents."""

    def __init__(self, output_dir: Path = Path("results/ocr_pipeline_evaluation/ground_truth")):
        """Initialize extractor.

        Args:
            output_dir: Directory to save ground truth files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def extract(self, html_path: Path, journal: str = "unknown") -> dict[str, Any]:
        """Extract ground truth from HTML file.

        Args:
            html_path: Path to HTML file
            journal: Journal name for metadata

        Returns:
            Ground truth data dict
        """
        logger.info(f"Extracting ground truth from {html_path.name}")

        try:
            with open(html_path, encoding="utf-8") as f:
                html_content = f.read()
        except UnicodeDecodeError:
            logger.warning(f"Unicode error reading {html_path}, trying latin-1")
            with open(html_path, encoding="latin-1") as f:
                html_content = f.read()

        soup = BeautifulSoup(html_content, "html.parser")

        # Extract ground truth
        ground_truth = {
            "file": html_path.name,
            "journal": journal,
            "body_text_paragraphs": self._extract_body_text(soup),
            "footnotes": self._extract_footnotes(soup),
            "headers": self._extract_headers(soup),
            "other_elements": self._extract_other_elements(soup),
            "metadata": {
                "total_body_paragraphs": 0,
                "total_footnotes": 0,
                "total_headers": 0,
                "total_other": 0,
            },
        }

        # Update counts
        ground_truth["metadata"]["total_body_paragraphs"] = len(
            ground_truth["body_text_paragraphs"]
        )
        ground_truth["metadata"]["total_footnotes"] = len(ground_truth["footnotes"])
        ground_truth["metadata"]["total_headers"] = len(ground_truth["headers"])
        ground_truth["metadata"]["total_other"] = len(ground_truth["other_elements"])

        # Save to file
        output_path = self.output_dir / f"{html_path.stem}_ground_truth.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(ground_truth, f, indent=2, ensure_ascii=False)

        logger.info(
            f"  ✓ Extracted: {len(ground_truth['body_text_paragraphs'])} body, "
            f"{len(ground_truth['footnotes'])} footnotes, "
            f"{len(ground_truth['headers'])} headers"
        )

        return ground_truth

    def _extract_body_text(self, soup: BeautifulSoup) -> list[dict[str, Any]]:
        """Extract body text paragraphs.

        Priority:
        1. Content within <article> tags
        2. Content in divs with class containing 'body', 'content', 'article'
        3. Standard <p> tags outside headers/footers/asides

        Args:
            soup: BeautifulSoup object

        Returns:
            List of body text paragraphs with metadata
        """
        body_texts = []

        # Strategy 1: Find <article> tags (semantic HTML5)
        articles = soup.find_all("article")
        if articles:
            for article in articles:
                for para in article.find_all("p"):
                    text = self._extract_text(para)
                    if self._is_valid_body_paragraph(text):
                        body_texts.append(
                            {
                                "text": text,
                                "source": "article_tag",
                                "length": len(text),
                            }
                        )

        # Strategy 2: Find divs with content-related classes
        content_divs = soup.find_all(
            "div",
            class_=re.compile(r"(body|content|article|main|text)", re.IGNORECASE),
        )
        for div in content_divs:
            for para in div.find_all("p", recursive=False):
                text = self._extract_text(para)
                if self._is_valid_body_paragraph(text) and text not in [
                    bt["text"] for bt in body_texts
                ]:
                    body_texts.append(
                        {
                            "text": text,
                            "source": "content_div",
                            "length": len(text),
                        }
                    )

        # Strategy 3: Find main <p> tags outside header/footer/aside
        if not body_texts:  # If no articles/content divs found
            for para in soup.find_all("p"):
                # Skip if in header, footer, aside, or nav
                parent = para.find_parent(["header", "footer", "aside", "nav"])
                if parent:
                    continue

                text = self._extract_text(para)
                if self._is_valid_body_paragraph(text):
                    body_texts.append(
                        {
                            "text": text,
                            "source": "p_tag",
                            "length": len(text),
                        }
                    )

        return body_texts

    def _extract_footnotes(self, soup: BeautifulSoup) -> list[dict[str, Any]]:
        """Extract footnotes and endnotes.

        Looks for:
        - Footnote list items within specific containers
        - Individual footnote content elements
        - Avoids page footers and navigation

        Args:
            soup: BeautifulSoup object

        Returns:
            List of footnotes with metadata
        """
        footnotes = []
        seen_texts = set()  # Avoid duplicates

        def normalize_for_dedup(text: str) -> str:
            """Normalize footnote text for deduplication."""
            # Remove common navigation text
            normalized = text.replace("Return to citation ^", "").replace("Return to citation", "")
            normalized = re.sub(r"^\^+", "", normalized)  # Remove leading ^ characters
            normalized = re.sub(r"\s+", " ", normalized)  # Normalize whitespace
            return normalized.strip()

        # Strategy 1: Find footnote lists (Harvard, Michigan, etc.)
        # Look for <li> elements with id like "footnote-ref-1" or class containing "footnote"
        for li in soup.find_all("li"):
            li_id = li.get("id", "").lower()
            li_class = " ".join(li.get("class", [])).lower()

            # Match footnote list items (not regular list items)
            if "footnote" in li_id or "footnote" in li_class:
                # Skip if it's a navigation or menu item
                if any(nav in li_class for nav in ["nav", "menu", "header"]):
                    continue

                text = self._extract_text(li)
                if text and len(text) > 20:  # Real footnote length
                    normalized = normalize_for_dedup(text)
                    if normalized and normalized not in seen_texts:
                        footnotes.append(
                            {
                                "text": text,
                                "source": "footnote_list_item",
                                "length": len(text),
                            }
                        )
                        seen_texts.add(normalized)

        # Strategy 2: Find <ol> or <ul> with footnote-related ids
        for list_elem in soup.find_all(["ol", "ul"]):
            list_id = list_elem.get("id", "").lower()
            if "footnote" in list_id or "endnote" in list_id or list_id in ["notes", "references"]:
                for li in list_elem.find_all("li", recursive=False):
                    text = self._extract_text(li)
                    if text and len(text) > 20:
                        normalized = normalize_for_dedup(text)
                        if normalized and normalized not in seen_texts:
                            footnotes.append(
                                {
                                    "text": text,
                                    "source": "footnote_list",
                                    "length": len(text),
                                }
                            )
                            seen_texts.add(normalized)

        # Strategy 3: Find footnote content paragraphs (for specific containers)
        # Look for divs/sections with "footnotes" in id or class
        for container in soup.find_all(["div", "section"]):
            container_id = container.get("id", "").lower()
            container_class = " ".join(container.get("class", [])).lower()

            if "footnote" in container_id or "footnote" in container_class:
                # Skip if it's just a footnote marker/button within body text
                if any(
                    skip in container_class
                    for skip in ["inline", "marker", "button", "show", "hide"]
                ):
                    continue

                # Extract <p> tags from footnote containers
                for para in container.find_all("p", recursive=True):
                    text = self._extract_text(para)
                    if text and len(text) > 20:
                        normalized = normalize_for_dedup(text)
                        if normalized and normalized not in seen_texts:
                            footnotes.append(
                                {
                                    "text": text,
                                    "source": "footnote_container",
                                    "length": len(text),
                                }
                            )
                            seen_texts.add(normalized)

        return footnotes

    def _extract_headers(self, soup: BeautifulSoup) -> list[dict[str, Any]]:
        """Extract headers and titles.

        Args:
            soup: BeautifulSoup object

        Returns:
            List of headers with metadata
        """
        headers = []

        # Find all heading tags
        for level in range(1, 7):  # h1 to h6
            for header in soup.find_all(f"h{level}"):
                text = self._extract_text(header)
                if text and len(text) > 2:  # Skip very short text
                    headers.append(
                        {
                            "text": text,
                            "source": f"h{level}",
                            "length": len(text),
                        }
                    )

        return headers

    def _extract_other_elements(self, soup: BeautifulSoup) -> list[dict[str, Any]]:
        """Extract other semantic elements (citations, lists, etc.).

        Args:
            soup: BeautifulSoup object

        Returns:
            List of other elements with metadata
        """
        other = []

        # Find citations
        for cite in soup.find_all("cite"):
            text = self._extract_text(cite)
            if text:
                other.append(
                    {
                        "text": text,
                        "type": "citation",
                        "source": "cite_tag",
                        "length": len(text),
                    }
                )

        # Find blockquotes
        for bq in soup.find_all("blockquote"):
            text = self._extract_text(bq)
            if text and len(text) > 10:
                other.append(
                    {
                        "text": text,
                        "type": "blockquote",
                        "source": "blockquote_tag",
                        "length": len(text),
                    }
                )

        return other

    def _extract_text(self, element: Any) -> str:
        """Extract and normalize text from element.

        Args:
            element: BeautifulSoup element

        Returns:
            Normalized text content
        """
        if not element:
            return ""

        # Clone the element to avoid modifying the original
        import copy

        elem_copy = copy.copy(element)

        # Remove inline footnote elements that contaminate body text:

        # 1. Tooltip-style footnotes (Michigan Law Review, etc.)
        for footnote_span in elem_copy.find_all("span", {"role": "tooltip"}):
            footnote_span.decompose()

        # 2. <cite> tag footnotes (UCLA Law Review, etc.)
        for cite in elem_copy.find_all("cite", class_=re.compile(r"footnote", re.IGNORECASE)):
            cite.decompose()

        # 3. Footnote markers and superscripts
        for sup in elem_copy.find_all("sup"):
            sup.decompose()

        # 4. Other footnote-related spans
        for footnote_elem in elem_copy.find_all(
            class_=re.compile(r"footnote.*note", re.IGNORECASE)
        ):
            if footnote_elem.name in ["span", "button"]:
                footnote_elem.decompose()

        # Get text and normalize
        text = elem_copy.get_text(strip=True)

        # Remove extra whitespace
        text = re.sub(r"\s+", " ", text)

        return text.strip()

    def _is_valid_body_paragraph(self, text: str) -> bool:
        """Check if text is likely a valid body paragraph.

        Args:
            text: Text to validate

        Returns:
            True if likely body text
        """
        # Minimum length (heuristic)
        if len(text) < 20:
            return False

        # Not just numbers/symbols
        if not re.search(r"[a-zA-Z]{5,}", text):
            return False

        # Not a page break marker or similar
        if text.lower() in ["page", "p.", "-", "---", "*", "***"]:
            return False

        return True


def main():
    """Extract ground truth from all HTML files."""
    extractor = HTMLGroundTruthExtractor()

    html_dir = Path("data/v3_data/raw_html")
    html_files = list(html_dir.glob("*.html"))

    logger.info(f"Processing {len(html_files)} HTML files")

    for i, html_file in enumerate(html_files, 1):
        logger.info(f"[{i}/{len(html_files)}] {html_file.name}")
        try:
            extractor.extract(html_file)
        except Exception as e:
            logger.error(f"  Error: {e}")

    logger.info("Ground truth extraction complete")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    main()
