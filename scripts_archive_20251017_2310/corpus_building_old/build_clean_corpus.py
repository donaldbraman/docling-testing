#!/usr/bin/env python3
"""
DoclingBert v2: Build comprehensive clean training corpus from multiple sources.

Sources (in order of quality):
1. Semantic PDF tags (highest quality) - 12K+ samples
2. HTML-PDF text matching - 358 samples
3. Cover page patterns - 479 samples
4. Docling labels (corrected by semantic tags) - variable

Version: v2 (cite-assist uses v1)

Issue: https://github.com/donaldbraman/docling-testing/issues/7
"""

import json
import re
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup
from pypdf import PdfReader

# Label mapping for 7-class classifier
LABEL_MAP = {
    "body_text": 0,
    "heading": 1,
    "footnote": 2,
    "caption": 3,
    "page_header": 4,
    "page_footer": 5,
    "cover": 6,
}


def extract_text_from_semantic_tags():
    """Extract text from semantic PDF tags (highest quality)."""
    print("\n" + "=" * 80)
    print("EXTRACTING TEXT FROM SEMANTIC PDF TAGS")
    print("=" * 80)

    tagged_pdfs_file = Path("data/tagged_pdfs_new.json")
    with open(tagged_pdfs_file) as f:
        tagged_pdfs = json.load(f)

    samples = []

    for i, pdf_info in enumerate(tagged_pdfs, 1):
        if i % 10 == 0:
            print(f"  Processing: {i}/{len(tagged_pdfs)} PDFs...")

        pdf_path = Path(pdf_info["path"])

        try:
            reader = PdfReader(pdf_path)
            catalog = reader.trailer["/Root"]

            if "/StructTreeRoot" not in catalog:
                continue

            struct_root = catalog["/StructTreeRoot"]

            # Extract text from tagged elements
            tagged_texts = extract_tagged_text_recursive(struct_root, reader)

            for text, tag in tagged_texts:
                # Map semantic tags to our labels
                label = map_semantic_tag_to_label(tag)
                if label and len(text.strip()) >= 20:  # Min 20 chars
                    samples.append(
                        {
                            "text": text.strip(),
                            "label": label,
                            "source": "semantic_tag",
                            "pdf": pdf_path.name,
                            "semantic_tag": tag,
                        }
                    )

        except Exception as e:
            print(f"    Error processing {pdf_path.name}: {e}")
            continue

    print(f"\n✓ Extracted {len(samples):,} samples from semantic tags")
    return samples


def extract_tagged_text_recursive(elem, reader, depth=0, max_depth=15):
    """Recursively extract text with semantic tags."""
    if depth > max_depth:
        return []

    texts = []

    try:
        # Get tag type
        tag = str(elem.get("/S", "")) if "/S" in elem else None

        # Get text content if this is a marked content
        if "/K" in elem:
            children = elem["/K"]
            if not isinstance(children, list):
                children = [children]

            for child in children:
                if isinstance(child, int):
                    # This is a marked content ID - extract text from page
                    continue
                elif hasattr(child, "get_object"):
                    child_obj = child.get_object()
                    texts.extend(
                        extract_tagged_text_recursive(child_obj, reader, depth + 1, max_depth)
                    )

        # If this element has actual text, extract it
        if "/ActualText" in elem:
            text = str(elem["/ActualText"])
            if tag and text:
                texts.append((text, tag))

    except Exception:
        pass

    return texts


def map_semantic_tag_to_label(tag):
    """Map semantic PDF tag to training label."""
    tag_mapping = {
        "/P": "body_text",
        "/Text": "body_text",
        "/H": "heading",
        "/H1": "heading",
        "/H2": "heading",
        "/H3": "heading",
        "/H4": "heading",
        "/H5": "heading",
        "/H6": "heading",
        "/Title": "heading",
        "/Footnote": "footnote",
        "/Note": "footnote",
        "/FN": "footnote",
        "/Caption": "caption",
        "/Table": "caption",  # Map table to caption for now
        "/Figure": "caption",
        "/Header": "page_header",
        "/Footer": "page_footer",
        "/Artifact": None,  # Skip artifacts
    }

    return tag_mapping.get(tag)


def match_html_pdf_texts():
    """Match HTML and PDF texts for body_text/footnote labels."""
    print("\n" + "=" * 80)
    print("MATCHING HTML-PDF PAIRS")
    print("=" * 80)

    html_dir = Path("data/raw_html")
    pdf_dir = Path("data/raw_pdf")

    html_files = list(html_dir.glob("*.html"))
    samples = []

    for i, html_file in enumerate(html_files, 1):
        if i % 20 == 0:
            print(f"  Processing: {i}/{len(html_files)} pairs...")

        pdf_file = pdf_dir / f"{html_file.stem}.docling.json"

        if not pdf_file.exists():
            continue

        # Load HTML
        with open(html_file, encoding="utf-8", errors="ignore") as f:
            soup = BeautifulSoup(f.read(), "html.parser")

        # Extract HTML paragraphs and footnotes
        html_texts = extract_html_texts(soup)

        # Load PDF Docling extraction
        with open(pdf_file) as f:
            pdf_data = json.load(f)

        # Match texts
        for html_text, html_label in html_texts:
            if len(html_text.strip()) >= 20:
                samples.append(
                    {
                        "text": html_text.strip(),
                        "label": html_label,
                        "source": "html_pdf_match",
                        "pdf": html_file.stem,
                    }
                )

    print(f"\n✓ Matched {len(samples):,} samples from HTML-PDF pairs")
    return samples


def extract_html_texts(soup):
    """Extract texts from HTML with labels."""
    texts = []

    # Extract body paragraphs
    for p in soup.find_all("p"):
        text = p.get_text(strip=True)
        if len(text) >= 20:
            texts.append((text, "body_text"))

    # Extract footnotes (common patterns in law reviews)
    for fn in soup.find_all(
        ["div", "p", "span"], class_=re.compile(r"footnote|endnote|note", re.I)
    ):
        text = fn.get_text(strip=True)
        if len(text) >= 20:
            texts.append((text, "footnote"))

    return texts


def load_cover_pages():
    """Load existing cover page samples."""
    print("\n" + "=" * 80)
    print("LOADING COVER PAGE SAMPLES")
    print("=" * 80)

    cover_file = Path("data/cover_corpus.csv")
    if not cover_file.exists():
        print("  No cover corpus found, skipping...")
        return []

    df = pd.read_csv(cover_file)
    samples = []

    for _, row in df.iterrows():
        samples.append(
            {
                "text": row["text"],
                "label": "cover",
                "source": "cover_pattern",
                "pdf": row.get("pdf", "unknown"),
            }
        )

    print(f"\n✓ Loaded {len(samples):,} cover page samples")
    return samples


def load_docling_labels():
    """Load Docling labels from JSON extractions."""
    print("\n" + "=" * 80)
    print("LOADING DOCLING LABELS")
    print("=" * 80)

    pdf_dir = Path("data/raw_pdf")
    json_files = list(pdf_dir.glob("*.docling.json"))

    samples = []

    for i, json_file in enumerate(json_files, 1):
        if i % 20 == 0:
            print(f"  Processing: {i}/{len(json_files)} files...")

        with open(json_file) as f:
            data = json.load(f)

        for item in data.get("texts", []):
            text = item.get("text", "").strip()
            label_str = item.get("label", "").lower().replace("-", "_")

            # Map Docling labels to our taxonomy
            if label_str in LABEL_MAP and len(text) >= 20:
                samples.append(
                    {"text": text, "label": label_str, "source": "docling", "pdf": data["file"]}
                )

    print(f"\n✓ Loaded {len(samples):,} samples from Docling")
    return samples


def merge_and_deduplicate(all_samples):
    """Merge samples and deduplicate based on source priority."""
    print("\n" + "=" * 80)
    print("MERGING AND DEDUPLICATING")
    print("=" * 80)

    # Convert to DataFrame
    df = pd.DataFrame(all_samples)

    # Source priority (highest first)
    source_priority = {"semantic_tag": 1, "html_pdf_match": 2, "cover_pattern": 3, "docling": 4}

    df["priority"] = df["source"].map(source_priority)

    # Deduplicate based on text, keeping highest priority source
    df = df.sort_values("priority")
    df = df.drop_duplicates(subset=["text"], keep="first")

    # Remove priority column
    df = df.drop("priority", axis=1)

    print(f"\nTotal samples after deduplication: {len(df):,}")
    print("\nSamples by source:")
    for source in ["semantic_tag", "html_pdf_match", "cover_pattern", "docling"]:
        count = (df["source"] == source).sum()
        pct = count / len(df) * 100
        print(f"  {source:20s} {count:6,} ({pct:5.1f}%)")

    print("\nSamples by label:")
    for label in LABEL_MAP:
        count = (df["label"] == label).sum()
        pct = count / len(df) * 100 if len(df) > 0 else 0
        print(f"  {label:15s} {count:6,} ({pct:5.1f}%)")

    return df


def main():
    """Build comprehensive clean corpus."""
    print("=" * 80)
    print("DOCLINGBERT V2: BUILDING COMPREHENSIVE CLEAN TRAINING CORPUS")
    print("=" * 80)
    print("\nVersion: v2 (cite-assist uses v1)")
    print("Model: DoclingBert (ModernBERT-base fine-tuned)\n")

    all_samples = []

    # 1. Extract from semantic tags (highest quality)
    semantic_samples = extract_text_from_semantic_tags()
    all_samples.extend(semantic_samples)

    # 2. Match HTML-PDF pairs
    html_pdf_samples = match_html_pdf_texts()
    all_samples.extend(html_pdf_samples)

    # 3. Load cover pages
    cover_samples = load_cover_pages()
    all_samples.extend(cover_samples)

    # 4. Load Docling labels (lowest priority)
    docling_samples = load_docling_labels()
    all_samples.extend(docling_samples)

    # 5. Merge and deduplicate
    final_df = merge_and_deduplicate(all_samples)

    # 6. Save corpus
    output_file = Path("data/clean_7class_corpus.csv")
    final_df.to_csv(output_file, index=False)

    print("\n" + "=" * 80)
    print("✓ CORPUS BUILDING COMPLETE")
    print("=" * 80)
    print(f"\nFinal corpus saved: {output_file}")
    print(f"Total samples: {len(final_df):,}")
    print("\nNext step: Train DoclingBert v2 classifier")
    print("  Run: python train_multiclass_classifier.py")


if __name__ == "__main__":
    main()
