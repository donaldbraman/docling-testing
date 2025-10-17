#!/usr/bin/env python3
"""
HTML/PDF Label Transfer Pipeline

Matches paragraphs between HTML (ground truth) and PDF (Docling extraction)
to create labeled training corpus without manual annotation.

Issue: https://github.com/donaldbraman/docling-testing/issues/4
"""

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import LayoutOptions, PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption


@dataclass
class Paragraph:
    """Represents a paragraph with its label and metadata."""

    text: str
    label: str  # 'body_text' or 'footnote'
    source: str  # 'html' or 'pdf'
    docling_label: str = None  # Docling's predicted label (PDF only)
    original_index: int = None


def normalize_text(text: str) -> str:
    """Normalize text for better matching."""
    # Remove extra whitespace
    text = re.sub(r"\s+", " ", text)
    # Remove hyphenation artifacts
    text = re.sub(r"-\s+", "", text)
    # Strip
    text = text.strip()
    return text


def extract_from_html(html_file: Path) -> list[Paragraph]:
    """
    Extract labeled paragraphs from HTML law review article.

    Supports multiple law review footnote patterns:
    1. Columbia Law Review: Inline <cite class="footnote">
    2. Harvard Law Review: List items <li id="footnote-ref-N">
    3. Michigan Law Review: <span class="modern-footnotes-footnote__note">
    4. Traditional: <div class="footnote">, <aside>, etc.

    See HTML_EXTRACTION_PATTERNS.md for full documentation.
    """
    # Try multiple encodings to handle different HTML files
    encodings = ["utf-8", "latin-1", "windows-1252", "iso-8859-1"]
    soup = None

    for encoding in encodings:
        try:
            with open(html_file, encoding=encoding) as f:
                soup = BeautifulSoup(f.read(), "html.parser")
            break
        except (UnicodeDecodeError, LookupError):
            continue

    if soup is None:
        print(f"  ⚠️  Could not decode {html_file.name} with any known encoding, skipping...")
        return []

    # Detect JavaScript-rendered content (skip if too few paragraphs)
    total_p_tags = len(soup.find_all("p"))
    if total_p_tags < 20:
        print(
            f"  ⚠️  Skipping {html_file.name}: JavaScript-rendered content ({total_p_tags} <p> tags)"
        )
        return []

    paragraphs = []

    # FOOTNOTE EXTRACTION (Pattern-Specific)

    # Pattern 1: Columbia Law Review - Inline <cite class="footnote">
    for cite in soup.find_all("cite", class_="footnote"):
        text_span = cite.find("span", class_="footnote-text")
        if text_span:
            text = normalize_text(text_span.get_text())
            # Remove footnote number prefix (e.g., "1. " or "1 ")
            text = re.sub(r"^\d+[\.\s]+", "", text)
            if len(text) > 20:
                paragraphs.append(
                    Paragraph(
                        text=text, label="footnote", source="html", original_index=len(paragraphs)
                    )
                )

    # Pattern 2: Harvard Law Review - List items <li id="footnote-ref-N">
    for li in soup.find_all("li", id=re.compile(r"footnote-ref-\d+")):
        content = li.find("p", class_="single-article-footnotes-list__item-content")
        if content:
            text = normalize_text(content.get_text())
            # Remove footnote number prefix
            text = re.sub(r"^\d+[\.\s]+", "", text)
            if len(text) > 20:
                paragraphs.append(
                    Paragraph(
                        text=text, label="footnote", source="html", original_index=len(paragraphs)
                    )
                )

    # Pattern 3: Michigan Law Review - <span class="modern-footnotes-footnote__note">
    for span in soup.find_all("span", class_="modern-footnotes-footnote__note"):
        text = normalize_text(span.get_text())
        if len(text) > 20:
            paragraphs.append(
                Paragraph(
                    text=text, label="footnote", source="html", original_index=len(paragraphs)
                )
            )

    # Pattern 4: Traditional container-based footnotes
    footnote_containers = [
        ".footnote",
        "aside",
        '[role="note"]',
        ".note",
        "#footnotes",
        "#footnote_wrapper",
    ]
    for selector in footnote_containers:
        for container in soup.select(selector):
            # Skip if already captured by pattern-specific extraction
            if container.find("cite", class_="footnote"):
                continue
            if container.find("li", id=re.compile(r"footnote-ref-")):
                continue
            if container.find("span", class_="modern-footnotes-footnote__note"):
                continue

            text = normalize_text(container.get_text())
            if len(text) > 20:
                # Check if not already captured
                if not any(p.text == text for p in paragraphs):
                    paragraphs.append(
                        Paragraph(
                            text=text,
                            label="footnote",
                            source="html",
                            original_index=len(paragraphs),
                        )
                    )

    # Yale Law Journal specific: Extract from footnote wrapper
    footnote_wrapper = soup.find("div", id="footnote_wrapper")
    if footnote_wrapper:
        for fn_div in footnote_wrapper.find_all("div", id=re.compile(r"^footnote_\d+$")):
            fn_content = fn_div.find("div", class_="truncated_footnote_inner")
            if fn_content:
                text = normalize_text(fn_content.get_text())
                if len(text) > 20:
                    # Check if not already captured
                    if not any(p.text == text for p in paragraphs):
                        paragraphs.append(
                            Paragraph(
                                text=text,
                                label="footnote",
                                source="html",
                                original_index=len(paragraphs),
                            )
                        )

    # BODY TEXT EXTRACTION

    # <p> tags not inside footnote containers
    for i, p in enumerate(soup.find_all("p")):
        # Check if paragraph is inside any footnote container
        is_footnote = False
        for selector in footnote_containers:
            if (
                p.find_parent(class_=selector.strip(".#[]"))
                or p.find_parent(id=selector.strip("#"))
                or (p.find_parent(selector.split("[")[0]) if "[" in selector else False)
            ):
                is_footnote = True
                break

        # Skip if inside modern-footnotes container
        if p.find_parent(class_="modern-footnotes-footnote__note"):
            is_footnote = True

        text = normalize_text(p.get_text())

        if len(text) > 50:  # Filter very short paragraphs
            if not is_footnote:
                paragraphs.append(
                    Paragraph(text=text, label="body_text", source="html", original_index=i)
                )

    return paragraphs


def extract_from_pdf(pdf_file: Path) -> list[Paragraph]:
    """
    Extract paragraphs from PDF using Docling.

    Captures both text and Docling's layout predictions for comparison.
    Uses caching to avoid re-extracting on subsequent runs.
    """
    import pickle

    # Check cache
    cache_file = pdf_file.with_suffix(".docling.pkl")
    if cache_file.exists():
        try:
            print(f"  Loading from cache: {pdf_file.name}...")
            with open(cache_file, "rb") as f:
                return pickle.load(f)
        except Exception as e:
            print(f"  Cache load failed ({e}), re-extracting...")

    # Extract from PDF
    pipeline = PdfPipelineOptions(
        layout_options=LayoutOptions(),
        generate_parsed_pages=True,
        generate_page_images=True,
        images_scale=1.0,
    )

    converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline)}
    )

    print(f"  Converting {pdf_file.name}...")
    result = converter.convert(str(pdf_file))
    doc = result.document

    paragraphs = []

    for i, (item, level) in enumerate(doc.iterate_items()):
        label = str(item.label) if hasattr(item, "label") else "NO_LABEL"
        text = normalize_text(item.text) if hasattr(item, "text") else ""

        if len(text) > 20:  # Filter very short items
            # Determine simplified label
            if "footnote" in label.lower():
                simplified_label = "footnote"
            elif label.lower() in ["text", "paragraph", "section_header", "list_item"]:
                simplified_label = "body_text"
            else:
                simplified_label = "unknown"

            paragraphs.append(
                Paragraph(
                    text=text,
                    label=simplified_label,  # Will be overwritten by HTML match
                    source="pdf",
                    docling_label=label,
                    original_index=i,
                )
            )

    # Cache results
    try:
        with open(cache_file, "wb") as f:
            pickle.dump(paragraphs, f)
    except Exception as e:
        print(f"  Warning: Failed to cache ({e})")

    return paragraphs


def match_paragraphs(
    html_paras: list[Paragraph], pdf_paras: list[Paragraph], similarity_threshold: float = 0.75
) -> pd.DataFrame:
    """
    Match HTML paragraphs to PDF paragraphs using fuzzy text matching.

    Transfers HTML ground truth labels to PDF extractions.

    Args:
        html_paras: Paragraphs extracted from HTML with ground truth labels
        pdf_paras: Paragraphs extracted from PDF via Docling
        similarity_threshold: Minimum similarity score (0-1) for matching

    Returns:
        DataFrame with matched paragraphs and transferred labels
    """
    matched_data = []
    unmatched_pdf = []

    for pdf_para in pdf_paras:
        pdf_text = pdf_para.text

        # Find best matching HTML paragraph
        best_match = None
        best_score = 0

        for html_para in html_paras:
            html_text = html_para.text

            # Calculate similarity using SequenceMatcher
            score = SequenceMatcher(None, pdf_text, html_text).ratio()

            if score > best_score:
                best_score = score
                best_match = html_para

        # Transfer label if good match
        if best_score >= similarity_threshold and best_match:
            matched_data.append(
                {
                    "text": pdf_text,  # Use PDF text (what model will see)
                    "html_label": best_match.label,  # Ground truth
                    "docling_label": pdf_para.docling_label,  # Docling's prediction
                    "similarity": best_score,
                    "html_index": best_match.original_index,
                    "pdf_index": pdf_para.original_index,
                }
            )
        else:
            unmatched_pdf.append(
                {
                    "text": pdf_text,
                    "docling_label": pdf_para.docling_label,
                    "best_score": best_score,
                }
            )

    # Create DataFrame
    df = pd.DataFrame(matched_data)

    # Print matching statistics
    print("\n  Matching Results:")
    print(f"    HTML paragraphs: {len(html_paras)}")
    print(f"    PDF paragraphs: {len(pdf_paras)}")
    if len(pdf_paras) > 0:
        print(f"    Matched: {len(df)} ({len(df) / len(pdf_paras) * 100:.1f}%)")
    else:
        print(f"    Matched: {len(df)} (0.0%)")
    print(f"    Unmatched: {len(unmatched_pdf)}")
    if len(df) > 0:
        print(f"    Avg similarity: {df['similarity'].mean():.2%}")
    else:
        print("    Avg similarity: N/A")

    if len(df) > 0:
        # Analyze label distribution
        print("\n  Label Distribution:")
        print(f"    Body text: {(df['html_label'] == 'body_text').sum()}")
        print(f"    Footnotes: {(df['html_label'] == 'footnote').sum()}")

        # Analyze Docling accuracy
        docling_correct = sum(
            ("footnote" in row["docling_label"].lower()) == (row["html_label"] == "footnote")
            for _, row in df.iterrows()
        )
        docling_accuracy = docling_correct / len(df) * 100
        print(f"\n  Docling Baseline Accuracy: {docling_accuracy:.1f}%")

    return df


def process_document_pair(html_file: Path, pdf_file: Path) -> pd.DataFrame:
    """Process a single HTML/PDF pair."""
    print(f"\n{'=' * 80}")
    print(f"Processing: {html_file.stem}")
    print(f"{'=' * 80}")

    # Extract from both sources
    print("\nExtracting from HTML...")
    html_paras = extract_from_html(html_file)
    print(f"  Found {len(html_paras)} paragraphs")

    print("\nExtracting from PDF...")
    pdf_paras = extract_from_pdf(pdf_file)
    print(f"  Found {len(pdf_paras)} paragraphs")

    # Match and transfer labels
    print("\nMatching paragraphs...")
    df = match_paragraphs(html_paras, pdf_paras)

    # Add document identifier
    df["document"] = html_file.stem

    return df


def process_pair_wrapper(args):
    """Wrapper for parallel processing."""
    html_file, pdf_file, output_dir = args
    try:
        df = process_document_pair(html_file, pdf_file)

        # Save individual pair results
        pair_output = output_dir / f"{html_file.stem}_matched.csv"
        df.to_csv(pair_output, index=False)
        print(f"  ✓ Saved: {pair_output}")

        return df
    except Exception as e:
        print(f"  ✗ Error processing {html_file.name}: {e}")
        import traceback

        traceback.print_exc()
        return None


def main():
    """Process all HTML/PDF pairs and create labeled corpus."""
    from concurrent.futures import ProcessPoolExecutor

    # Get project root (2 levels up from scripts/corpus_building)
    base_dir = Path(__file__).parent.parent.parent

    html_dir = base_dir / "data" / "raw_html"
    pdf_dir = base_dir / "data" / "raw_pdf"
    output_dir = base_dir / "data" / "html_pdf_pairs"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Find matching HTML/PDF pairs
    html_files = sorted(html_dir.glob("*.html"))

    if not html_files:
        print("No HTML files found in data/raw_html/")
        print("\nTo use this script:")
        print("1. Place HTML law review articles in data/raw_html/")
        print("2. Place matching PDF files in data/raw_pdf/")
        print("3. Run: python match_html_pdf.py")
        return

    # Find valid pairs with quality filtering
    pairs = []
    skipped_small = []

    for html_file in html_files:
        pdf_file = pdf_dir / f"{html_file.stem}.pdf"
        if not pdf_file.exists():
            print(f"⚠️  No matching PDF for {html_file.name}, skipping...")
            continue

        # Quality filter: Skip likely book reviews/short essays
        html_size = html_file.stat().st_size
        pdf_size = pdf_file.stat().st_size

        # Full articles typically have:
        # - HTML > 50 KB (with full footnotes)
        # - PDF > 200 KB (substantial content)
        if html_size < 50_000 or pdf_size < 200_000:
            skipped_small.append(html_file.name)
            continue

        pairs.append((html_file, pdf_file, output_dir))

    if skipped_small:
        print(f"\n⚠️  Skipped {len(skipped_small)} small pairs (likely book reviews/essays):")
        for name in skipped_small[:5]:
            print(f"    - {name}")
        if len(skipped_small) > 5:
            print(f"    ... and {len(skipped_small) - 5} more")

    print(f"\n{'=' * 80}")
    print(f"PARALLEL PROCESSING: {len(pairs)} pairs with 8 workers")
    print(f"{'=' * 80}\n")

    # Process in parallel
    all_data = []
    with ProcessPoolExecutor(max_workers=8) as executor:
        results = executor.map(process_pair_wrapper, pairs)
        all_data = [df for df in results if df is not None]

    print(f"\n{'=' * 80}")
    print("All pairs processed")
    print(f"{'=' * 80}")

    # Combine all pairs into training corpus
    if all_data:
        combined_df = pd.concat(all_data, ignore_index=True)
        corpus_path = base_dir / "data" / "labeled_pdf_corpus.csv"
        combined_df.to_csv(corpus_path, index=False)

        print(f"\n{'=' * 80}")
        print("CORPUS GENERATED")
        print(f"{'=' * 80}")
        print(f"\nTotal labeled paragraphs: {len(combined_df):,}")
        print(f"  Body text: {(combined_df['html_label'] == 'body_text').sum():,}")
        print(f"  Footnotes: {(combined_df['html_label'] == 'footnote').sum():,}")
        print(f"\nAverage similarity: {combined_df['similarity'].mean():.2%}")
        print(f"Saved to: {corpus_path}")
        print("\n✓ Ready for model training!")
    else:
        print("\n⚠️  No document pairs processed")


if __name__ == "__main__":
    main()
