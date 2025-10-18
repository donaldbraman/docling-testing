#!/usr/bin/env python3
"""
Merge all corpuses and map Docling labels to 8 training classes.

Maps Docling's native labels to research-backed 8-class taxonomy:
- body_text: Main article content (paragraphs, lists)
- heading: Titles and section headers
- footnote: Footnote text
- reference: Bibliography entries
- caption: Figure and table captions
- table: Table content
- page_header: Running headers
- page_footer: Running footers with page numbers
- cover: Cover/title pages

Based on DocBank/PubLayNet research for optimal classification.

Issue: https://github.com/donaldbraman/docling-testing/issues/7
"""

from pathlib import Path

import pandas as pd

# Docling label → Training class mapping (8 classes)
LABEL_MAPPING = {
    # Body text (main content)
    "text": "body_text",
    "paragraph": "body_text",
    "list_item": "body_text",
    # Headings (titles and sections)
    "title": "heading",
    "section_header": "heading",
    # Structural elements
    "footnote": "footnote",
    "reference": "reference",
    "caption": "caption",
    "table": "table",
    "page_header": "page_header",
    "page_footer": "page_footer",
    # Cover (from pattern-detected corpus)
    "cover": "cover",
    "cover_heinonline": "cover",
    "cover_jstor": "cover",
    # Additional Docling labels (map to most appropriate class)
    "list": "body_text",
    "figure": "caption",  # Treat figure markers as captions
    "equation": "body_text",  # Rare, treat as body text
    "abstract": "body_text",  # Abstract is body content
    "author": "heading",  # Author names are heading-like
}


def load_full_docling_corpus(path: Path) -> pd.DataFrame:
    """Load full Docling extraction corpus."""
    if not path.exists():
        raise FileNotFoundError(
            f"Full Docling corpus not found: {path}\n"
            "Wait for extract_all_docling_labels.py to complete"
        )

    df = pd.read_csv(path)
    print(f"\n✓ Loaded full Docling corpus: {len(df):,} paragraphs")
    print("\nDocling label distribution:")
    for label, count in df["docling_label"].value_counts().items():
        print(f"  {label:20s} {count:5,}")

    return df


def load_cover_corpus(path: Path) -> pd.DataFrame:
    """Load cover pages corpus."""
    if not path.exists():
        print(f"\n⚠️  Cover corpus not found: {path}")
        return pd.DataFrame()

    df = pd.read_csv(path)
    print(f"\n✓ Loaded cover corpus: {len(df):,} paragraphs")

    return df


def map_to_training_classes(df: pd.DataFrame) -> pd.DataFrame:
    """Map Docling labels to 8 training classes."""

    # Determine source label column
    if "label" in df.columns:
        source_col = "label"
    elif "docling_label" in df.columns:
        source_col = "docling_label"
    else:
        raise ValueError("DataFrame must have 'label' or 'docling_label' column")

    # Map to training classes
    def map_label(label):
        if label in LABEL_MAPPING:
            return LABEL_MAPPING[label]
        else:
            print(f"\n⚠️  Unknown label '{label}' - skipping")
            return None

    df["training_label"] = df[source_col].apply(map_label)

    # Remove unmapped labels
    before_len = len(df)
    df = df[df["training_label"].notna()].copy()
    after_len = len(df)

    if before_len != after_len:
        print(f"\n⚠️  Removed {before_len - after_len} paragraphs with unmapped labels")

    return df


def merge_corpuses(full_docling_path: Path, cover_path: Path, output_path: Path):
    """Merge all corpuses and apply label mapping."""

    print("=" * 80)
    print("MERGING CORPUSES WITH 8-CLASS LABEL MAPPING")
    print("=" * 80)

    # Load corpuses
    docling_df = load_full_docling_corpus(full_docling_path)
    cover_df = load_cover_corpus(cover_path)

    # Map labels
    print("\n" + "=" * 80)
    print("MAPPING LABELS")
    print("=" * 80)

    print("\nMapping Docling labels to training classes...")
    docling_df = map_to_training_classes(docling_df)

    if not cover_df.empty:
        print("\nMapping cover corpus labels...")
        cover_df = map_to_training_classes(cover_df)

    # Merge
    print("\n" + "=" * 80)
    print("MERGING")
    print("=" * 80)

    all_dfs = [docling_df]
    if not cover_df.empty:
        all_dfs.append(cover_df)

    merged_df = pd.concat(all_dfs, ignore_index=True)

    # Standardize columns
    final_df = pd.DataFrame(
        {
            "text": merged_df["text"],
            "label": merged_df["training_label"],
            "source": merged_df["source"],
            "original_label": merged_df.get("docling_label", merged_df.get("label")),
        }
    )

    # Remove duplicates
    before_len = len(final_df)
    final_df = final_df.drop_duplicates(subset=["text"]).copy()
    after_len = len(final_df)

    if before_len != after_len:
        print(f"\n✓ Removed {before_len - after_len} duplicate paragraphs")

    # Show final distribution
    print("\n" + "=" * 80)
    print("FINAL 8-CLASS CORPUS")
    print("=" * 80)
    print(f"\nTotal paragraphs: {len(final_df):,}")
    print("\nTraining class distribution:")

    for label, count in final_df["label"].value_counts().items():
        percentage = (count / len(final_df)) * 100
        print(f"  {label:15s} {count:6,} ({percentage:5.1f}%)")

    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    final_df.to_csv(output_path, index=False)

    print(f"\n✓ Saved 8-class corpus: {output_path}")
    print(f"  Size: {output_path.stat().st_size / 1024 / 1024:.2f} MB")

    return final_df


def main():
    """Main pipeline."""
    base_dir = Path(__file__).parent

    # Input paths
    full_docling_path = base_dir / "data" / "full_docling_corpus.csv"
    cover_path = base_dir / "data" / "cover_pages_corpus.csv"

    # Output path
    output_path = base_dir / "data" / "8class_corpus.csv"

    # Merge
    merged_df = merge_corpuses(full_docling_path, cover_path, output_path)

    # Validate minimum samples per class
    print("\n" + "=" * 80)
    print("VALIDATION")
    print("=" * 80)

    MIN_SAMPLES = 50
    class_counts = merged_df["label"].value_counts()

    print(f"\nChecking minimum samples per class (threshold={MIN_SAMPLES}):")
    issues = []
    for label, count in class_counts.items():
        status = "✓" if count >= MIN_SAMPLES else "⚠️"
        print(f"  {status} {label:15s} {count:6,}")
        if count < MIN_SAMPLES:
            issues.append(f"{label} ({count} samples)")

    if issues:
        print(f"\n⚠️  Warning: Low sample counts for: {', '.join(issues)}")
        print("   Consider collecting more training data for these classes")
    else:
        print(f"\n✓ All classes have at least {MIN_SAMPLES} samples")

    print("\n" + "=" * 80)
    print("✓ CORPUS MERGE COMPLETE")
    print("=" * 80)
    print("\nNext step: python train_multiclass_classifier.py")


if __name__ == "__main__":
    main()
