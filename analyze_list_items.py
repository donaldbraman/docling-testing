#!/usr/bin/env python3
"""Analyze list_item labels to distinguish citations from real content."""

import pickle
from pathlib import Path
import re

# Load pickled document
pkl_path = Path('results/saved_vs_fresh/Jackson_2014_default_doc.pkl')
with open(pkl_path, 'rb') as f:
    doc = pickle.load(f)

print("Analyzing list_item labels:\n")

list_items = []
for item, level in doc.iterate_items():
    label = str(item.label) if hasattr(item, 'label') else 'NO_LABEL'
    text = (item.text if hasattr(item, 'text') else '').strip()

    if label == 'list_item':
        list_items.append(text)

print(f"Total list_item count: {len(list_items)}\n")

# Categorize list items
short_citations = []  # Likely footnote citations
long_items = []  # Likely real list items

for text in list_items:
    if len(text) < 100 and re.match(r'^\d+.*\d+.*\(.*\d{4}.*\)', text[:60]):
        # Looks like a short legal citation (year, case number, etc.)
        short_citations.append(text)
    else:
        long_items.append(text)

print(f"Short citations (likely footnotes): {len(short_citations)}")
print("\nExamples:")
for cite in short_citations[:15]:
    print(f"  {cite}")

print(f"\n\nLong list items (likely real content): {len(long_items)}")
print("\nExamples:")
for item in long_items[:10]:
    preview = item if len(item) < 120 else item[:120] + "..."
    print(f"  {preview}")
