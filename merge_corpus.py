#!/usr/bin/env python3
"""
Merge footnote/body_text corpus with cover page corpus for multi-class training.

Creates unified corpus with 3 classes:
- body_text
- footnote
- cover (heinonline + jstor combined)
"""

from pathlib import Path
import pandas as pd


def main():
    """Merge corpuses for multi-class training."""
    base_dir = Path(__file__).parent
    data_dir = base_dir / "data"

    # Load existing corpuses
    body_footnote_path = data_dir / "labeled_pdf_corpus.csv"
    covers_path = data_dir / "cover_pages_corpus.csv"
    output_path = data_dir / "multiclass_corpus.csv"

    print("Loading corpuses...")
    print("=" * 80)

    # Load body_text and footnote samples
    df_body_footnote = pd.read_csv(body_footnote_path)
    print(f"✓ Body/footnote corpus: {len(df_body_footnote)} samples")
    print(f"  - body_text: {len(df_body_footnote[df_body_footnote['html_label'] == 'body_text'])}")
    print(f"  - footnote:  {len(df_body_footnote[df_body_footnote['html_label'] == 'footnote'])}")

    # Load cover samples
    df_covers = pd.read_csv(covers_path)
    print(f"\n✓ Cover corpus: {len(df_covers)} samples")
    print(f"  - cover_heinonline: {len(df_covers[df_covers['label'] == 'cover_heinonline'])}")
    print(f"  - cover_jstor:      {len(df_covers[df_covers['label'] == 'cover_jstor'])}")

    # Standardize columns
    # Body/footnote has: document, text, html_label, ...
    # Covers has: text, label, source, extraction_method

    df_body_footnote = df_body_footnote.rename(columns={'html_label': 'label', 'document': 'source'})
    df_body_footnote = df_body_footnote[['text', 'label', 'source']]

    # Combine heinonline and jstor into single 'cover' class
    df_covers['label'] = 'cover'
    df_covers = df_covers[['text', 'label', 'source']]

    # Merge
    df_merged = pd.concat([df_body_footnote, df_covers], ignore_index=True)

    # Shuffle
    df_merged = df_merged.sample(frac=1, random_state=42).reset_index(drop=True)

    # Save
    df_merged.to_csv(output_path, index=False)

    print("\n" + "=" * 80)
    print("MERGED CORPUS")
    print("=" * 80)
    print(f"Total samples: {len(df_merged)}")
    print("\nClass distribution:")
    print(df_merged['label'].value_counts().to_string())

    print(f"\n✓ Saved to: {output_path}")

    # Calculate class balance
    class_counts = df_merged['label'].value_counts()
    print("\n" + "=" * 80)
    print("CLASS BALANCE ANALYSIS")
    print("=" * 80)
    for label, count in class_counts.items():
        percentage = (count / len(df_merged)) * 100
        print(f"{label:15s} {count:5d} ({percentage:5.1f}%)")

    # Check for imbalance
    max_count = class_counts.max()
    min_count = class_counts.min()
    imbalance_ratio = max_count / min_count

    print(f"\nImbalance ratio: {imbalance_ratio:.2f}:1")
    if imbalance_ratio > 3:
        print("⚠️  Significant class imbalance - consider using class weights in training")
    else:
        print("✓ Reasonable class balance")


if __name__ == "__main__":
    main()
