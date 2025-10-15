#!/usr/bin/env python3
"""Check labels assigned to numbered items."""

import pickle
from pathlib import Path

# Load pickled document
pkl_path = Path("results/saved_vs_fresh/Jackson_2014_default_doc.pkl")
with open(pkl_path, "rb") as f:
    doc = pickle.load(f)

print("Items starting with numbers:\n")
print(f"{'Label':<20} | {'Text Preview':<80}")
print("=" * 105)

count = 0
for item, level in doc.iterate_items():
    label = str(item.label) if hasattr(item, "label") else "NO_LABEL"
    text = (item.text if hasattr(item, "text") else "").strip()

    # Check if text starts with a number followed by period
    if text and text[0].isdigit() and ". " in text[:10]:
        print(f"{label:<20} | {text[:80]}")
        count += 1
        if count > 50:  # Limit output
            print("\n... (truncated)")
            break

print(f"\nTotal numbered items found: {count}")
