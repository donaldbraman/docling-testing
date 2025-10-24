#!/usr/bin/env python3
"""
Analyze results filtering for law review articles only.

Law reviews are single-column academic journals, unlike multi-column formats
like The Supreme Court Review.
"""

from pathlib import Path

import pandas as pd

# Read results
results_file = Path("results/sequence_alignment/full_evaluation/all_pdfs_results.csv")
df = pd.read_csv(results_file)

# Identify law review articles
law_review_journals = [
    "harvard_law_review_",
    "california_law_review_",
    "michigan_law_review_",
    "texas_law_review_",
    "bu_law_review_",
    "usc_law_review_",
    "ucla_law_review_",
    "virginia_law_review_",
    "wisconsin_law_review_",
]

# Filter for law reviews
df["is_law_review"] = df["pdf_name"].apply(
    lambda x: any(x.startswith(journal) for journal in law_review_journals)
)

law_reviews = df[df["is_law_review"]]
non_law_reviews = df[~df["is_law_review"]]

print("=" * 80)
print("LAW REVIEW vs NON-LAW REVIEW COMPARISON")
print("=" * 80)

print("\n📊 Dataset Split:")
print(f"  Law Reviews: {len(law_reviews)} PDFs")
print(f"  Non-Law Reviews: {len(non_law_reviews)} PDFs")
print(f"  Total: {len(df)} PDFs")

print("\n" + "=" * 80)
print("LAW REVIEW ARTICLES ONLY")
print("=" * 80)

print("\n📊 Macro F1 Statistics:")
print(f"  Mean:   {law_reviews['macro_f1'].mean():.3f}")
print(f"  Median: {law_reviews['macro_f1'].median():.3f}")
print(f"  Std:    {law_reviews['macro_f1'].std():.3f}")
print(f"  Min:    {law_reviews['macro_f1'].min():.3f}")
print(f"  Max:    {law_reviews['macro_f1'].max():.3f}")

print("\n📊 Body F1 Statistics:")
print(f"  Mean:   {law_reviews['body_f1'].mean():.3f}")
print(f"  Median: {law_reviews['body_f1'].median():.3f}")
print(f"  Std:    {law_reviews['body_f1'].std():.3f}")

print("\n📊 Footnote F1 Statistics:")
print(f"  Mean:   {law_reviews['footnote_f1'].mean():.3f}")
print(f"  Median: {law_reviews['footnote_f1'].median():.3f}")
print(f"  Std:    {law_reviews['footnote_f1'].std():.3f}")

# Performance distribution
perfect = len(law_reviews[law_reviews["macro_f1"] == 1.0])
excellent = len(law_reviews[(law_reviews["macro_f1"] >= 0.95) & (law_reviews["macro_f1"] < 1.0)])
good = len(law_reviews[(law_reviews["macro_f1"] >= 0.8) & (law_reviews["macro_f1"] < 0.95)])
fair = len(law_reviews[(law_reviews["macro_f1"] >= 0.6) & (law_reviews["macro_f1"] < 0.8)])
poor = len(law_reviews[law_reviews["macro_f1"] < 0.6])

print("\n📊 Performance Distribution (Macro F1):")
print(f"  Perfect (1.00):        {perfect:3d} ({perfect / len(law_reviews) * 100:.1f}%)")
print(f"  Excellent (0.95-1.00): {excellent:3d} ({excellent / len(law_reviews) * 100:.1f}%)")
print(f"  Good (0.80-0.95):      {good:3d} ({good / len(law_reviews) * 100:.1f}%)")
print(f"  Fair (0.60-0.80):      {fair:3d} ({fair / len(law_reviews) * 100:.1f}%)")
print(f"  Poor (<0.60):          {poor:3d} ({poor / len(law_reviews) * 100:.1f}%)")

print("\n" + "=" * 80)
print("NON-LAW REVIEW ARTICLES")
print("=" * 80)

print("\n📊 Macro F1 Statistics:")
print(f"  Mean:   {non_law_reviews['macro_f1'].mean():.3f}")
print(f"  Median: {non_law_reviews['macro_f1'].median():.3f}")
print(f"  Std:    {non_law_reviews['macro_f1'].std():.3f}")

print("\n📊 Body F1 Statistics:")
print(f"  Mean:   {non_law_reviews['body_f1'].mean():.3f}")

print("\n📊 Footnote F1 Statistics:")
print(f"  Mean:   {non_law_reviews['footnote_f1'].mean():.3f}")

print("\n" + "=" * 80)
print("COMPARISON")
print("=" * 80)

print("\n📊 Macro F1 Difference:")
print(f"  Law Reviews:     {law_reviews['macro_f1'].mean():.3f}")
print(f"  Non-Law Reviews: {non_law_reviews['macro_f1'].mean():.3f}")
print(
    f"  Difference:      {law_reviews['macro_f1'].mean() - non_law_reviews['macro_f1'].mean():+.3f}"
)

print("\n📊 Body F1 Difference:")
print(f"  Law Reviews:     {law_reviews['body_f1'].mean():.3f}")
print(f"  Non-Law Reviews: {non_law_reviews['body_f1'].mean():.3f}")
print(
    f"  Difference:      {law_reviews['body_f1'].mean() - non_law_reviews['body_f1'].mean():+.3f}"
)

print("\n📊 Footnote F1 Difference:")
print(f"  Law Reviews:     {law_reviews['footnote_f1'].mean():.3f}")
print(f"  Non-Law Reviews: {non_law_reviews['footnote_f1'].mean():.3f}")
print(
    f"  Difference:      {law_reviews['footnote_f1'].mean() - non_law_reviews['footnote_f1'].mean():+.3f}"
)

# Show worst performing law reviews
if len(law_reviews[law_reviews["macro_f1"] < 0.9]) > 0:
    print("\n📊 Law Reviews with Macro F1 < 0.90:")
    worst = law_reviews[law_reviews["macro_f1"] < 0.9].sort_values("macro_f1")
    for _, row in worst.iterrows():
        print(
            f"  {row['pdf_name'][:60]:60s} | Macro: {row['macro_f1']:.3f} | "
            f"Body: {row['body_f1']:.3f} | Footnote: {row['footnote_f1']:.3f}"
        )

print("\n" + "=" * 80)
print("ANALYSIS COMPLETE")
print("=" * 80)
