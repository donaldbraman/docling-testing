#!/usr/bin/env python3
"""
HTML/PDF Label Transfer Pipeline

Matches paragraphs between HTML (ground truth) and PDF (Docling extraction)
to create labeled training corpus without manual annotation.

Issue: https://github.com/donaldbraman/docling-testing/issues/4
"""

import re
from pathlib import Path
from difflib import SequenceMatcher
from typing import List, Dict, Tuple
from dataclasses import dataclass

import pandas as pd
from bs4 import BeautifulSoup
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, LayoutOptions
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
    text = re.sub(r'\s+', ' ', text)
    # Remove hyphenation artifacts
    text = re.sub(r'-\s+', '', text)
    # Strip
    text = text.strip()
    return text


def extract_from_html(html_file: Path) -> List[Paragraph]:
    """
    Extract labeled paragraphs from HTML law review article.

    HTML provides semantic ground truth via tags:
    - <p> (not in footnotes) = body text
    - <div class="footnote">, <aside>, etc. = footnotes
    """
    soup = BeautifulSoup(open(html_file, encoding='utf-8'), 'html.parser')

    paragraphs = []

    # Body text: <p> tags not inside footnote containers
    footnote_containers = ['.footnote', 'aside', '[role="note"]', '.note', '#footnotes']

    for i, p in enumerate(soup.find_all('p')):
        # Check if paragraph is inside any footnote container
        is_footnote = False
        for selector in footnote_containers:
            if p.find_parent(class_=selector.strip('.#[]')) or \
               p.find_parent(selector.split('[')[0]) if '[' in selector else False:
                is_footnote = True
                break

        text = normalize_text(p.get_text())

        if len(text) > 50:  # Filter very short paragraphs
            label = 'footnote' if is_footnote else 'body_text'
            paragraphs.append(Paragraph(
                text=text,
                label=label,
                source='html',
                original_index=i
            ))

    # Explicit footnote elements
    for selector in footnote_containers:
        for fn in soup.select(selector):
            text = normalize_text(fn.get_text())
            if len(text) > 20:
                # Check if not already captured
                if not any(p.text == text for p in paragraphs):
                    paragraphs.append(Paragraph(
                        text=text,
                        label='footnote',
                        source='html',
                        original_index=len(paragraphs)
                    ))

    return paragraphs


def extract_from_pdf(pdf_file: Path) -> List[Paragraph]:
    """
    Extract paragraphs from PDF using Docling.

    Captures both text and Docling's layout predictions for comparison.
    """
    # Use default config (same as experiments)
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
        label = str(item.label) if hasattr(item, 'label') else "NO_LABEL"
        text = normalize_text(item.text) if hasattr(item, 'text') else ""

        if len(text) > 20:  # Filter very short items
            # Determine simplified label
            if 'footnote' in label.lower():
                simplified_label = 'footnote'
            elif label.lower() in ['text', 'paragraph', 'section_header', 'list_item']:
                simplified_label = 'body_text'
            else:
                simplified_label = 'unknown'

            paragraphs.append(Paragraph(
                text=text,
                label=simplified_label,  # Will be overwritten by HTML match
                source='pdf',
                docling_label=label,
                original_index=i
            ))

    return paragraphs


def match_paragraphs(
    html_paras: List[Paragraph],
    pdf_paras: List[Paragraph],
    similarity_threshold: float = 0.75
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
            matched_data.append({
                'text': pdf_text,  # Use PDF text (what model will see)
                'html_label': best_match.label,  # Ground truth
                'docling_label': pdf_para.docling_label,  # Docling's prediction
                'similarity': best_score,
                'html_index': best_match.original_index,
                'pdf_index': pdf_para.original_index,
            })
        else:
            unmatched_pdf.append({
                'text': pdf_text,
                'docling_label': pdf_para.docling_label,
                'best_score': best_score,
            })

    # Create DataFrame
    df = pd.DataFrame(matched_data)

    # Print matching statistics
    print(f"\n  Matching Results:")
    print(f"    HTML paragraphs: {len(html_paras)}")
    print(f"    PDF paragraphs: {len(pdf_paras)}")
    print(f"    Matched: {len(df)} ({len(df)/len(pdf_paras)*100:.1f}%)")
    print(f"    Unmatched: {len(unmatched_pdf)}")
    print(f"    Avg similarity: {df['similarity'].mean():.2%}")

    if len(df) > 0:
        # Analyze label distribution
        print(f"\n  Label Distribution:")
        print(f"    Body text: {(df['html_label']=='body_text').sum()}")
        print(f"    Footnotes: {(df['html_label']=='footnote').sum()}")

        # Analyze Docling accuracy
        docling_correct = sum(
            ('footnote' in row['docling_label'].lower()) == (row['html_label'] == 'footnote')
            for _, row in df.iterrows()
        )
        docling_accuracy = docling_correct / len(df) * 100
        print(f"\n  Docling Baseline Accuracy: {docling_accuracy:.1f}%")

    return df


def process_document_pair(html_file: Path, pdf_file: Path) -> pd.DataFrame:
    """Process a single HTML/PDF pair."""
    print(f"\n{'='*80}")
    print(f"Processing: {html_file.stem}")
    print(f"{'='*80}")

    # Extract from both sources
    print(f"\nExtracting from HTML...")
    html_paras = extract_from_html(html_file)
    print(f"  Found {len(html_paras)} paragraphs")

    print(f"\nExtracting from PDF...")
    pdf_paras = extract_from_pdf(pdf_file)
    print(f"  Found {len(pdf_paras)} paragraphs")

    # Match and transfer labels
    print(f"\nMatching paragraphs...")
    df = match_paragraphs(html_paras, pdf_paras)

    # Add document identifier
    df['document'] = html_file.stem

    return df


def main():
    """Process all HTML/PDF pairs and create labeled corpus."""
    base_dir = Path(__file__).parent

    # Example: Process pairs if available
    # User needs to provide HTML/PDF pairs

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

    all_data = []

    for html_file in html_files:
        # Find matching PDF
        pdf_file = pdf_dir / f"{html_file.stem}.pdf"

        if not pdf_file.exists():
            print(f"⚠️  No matching PDF for {html_file.name}, skipping...")
            continue

        try:
            df = process_document_pair(html_file, pdf_file)
            all_data.append(df)

            # Save individual pair results
            pair_output = output_dir / f"{html_file.stem}_matched.csv"
            df.to_csv(pair_output, index=False)
            print(f"  ✓ Saved: {pair_output}")

        except Exception as e:
            print(f"  ✗ Error processing {html_file.name}: {e}")
            import traceback
            traceback.print_exc()

    # Combine all pairs into training corpus
    if all_data:
        combined_df = pd.concat(all_data, ignore_index=True)
        corpus_path = base_dir / "data" / "labeled_pdf_corpus.csv"
        combined_df.to_csv(corpus_path, index=False)

        print(f"\n{'='*80}")
        print(f"CORPUS GENERATED")
        print(f"{'='*80}")
        print(f"\nTotal labeled paragraphs: {len(combined_df):,}")
        print(f"  Body text: {(combined_df['html_label']=='body_text').sum():,}")
        print(f"  Footnotes: {(combined_df['html_label']=='footnote').sum():,}")
        print(f"\nAverage similarity: {combined_df['similarity'].mean():.2%}")
        print(f"Saved to: {corpus_path}")
        print(f"\n✓ Ready for model training!")
    else:
        print("\n⚠️  No document pairs processed")


if __name__ == "__main__":
    main()
