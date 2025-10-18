#!/usr/bin/env python3
"""Debug what BeautifulSoup passes to the lambda."""

from pathlib import Path

from bs4 import BeautifulSoup

html_file = Path("data/v3_data/raw_html/harvard_law_review_excited_delirium.html")

with open(html_file, encoding="utf-8") as f:
    soup = BeautifulSoup(f.read(), "html.parser")

# Remove script/style
for script in soup(["script", "style"]):
    script.decompose()

print("=== Debugging lambda input ===")
print("Looking for divs with 'footnote' in class...")

call_count = [0]  # Use list to allow modification in lambda
matches = [0]


def debug_lambda(x):
    call_count[0] += 1
    if call_count[0] <= 5:  # Only print first 5 calls
        print(f"\nCall {call_count[0]}:")
        print(f"  Input: {x}")
        print(f"  Type: {type(x)}")
        if x:
            joined = " ".join(x).lower() if isinstance(x, list) else str(x).lower()
            print(f"  Joined/str: '{joined}'")
            has_footnote = "footnote" in joined
            print(f"  Has 'footnote': {has_footnote}")
            if has_footnote:
                matches[0] += 1
                print("  *** MATCH! ***")
            return has_footnote
    return False


result = soup.find_all(["div", "section", "aside"], class_=debug_lambda)
print("\n=== Results ===")
print(f"Total calls to lambda: {call_count[0]}")
print(f"Matches found: {matches[0]}")
print(f"Elements returned by find_all: {len(result)}")
