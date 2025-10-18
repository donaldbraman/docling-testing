#!/usr/bin/env python3
"""Debug the any() issue in lambda."""

from pathlib import Path

from bs4 import BeautifulSoup

html_file = Path("data/v3_data/raw_html/harvard_law_review_excited_delirium.html")

with open(html_file, encoding="utf-8") as f:
    soup = BeautifulSoup(f.read(), "html.parser")

print("=== Test 1: Lambda with just 'footnote' check (no any()) ===")
test1 = soup.find_all(
    ["div", "section", "aside"], class_=lambda x: x and "footnote" in " ".join(x).lower()
)
print(f"Found: {len(test1)}")

print("\n=== Test 2: Lambda with any() and single marker ===")
test2 = soup.find_all(
    ["div", "section", "aside"],
    class_=lambda x: x and any(marker in " ".join(x).lower() for marker in ["footnote"]),
)
print(f"Found: {len(test2)}")

print("\n=== Test 3: Lambda with any() and three markers (original) ===")
test3 = soup.find_all(
    ["div", "section", "aside"],
    class_=lambda x: x
    and any(marker in " ".join(x).lower() for marker in ["footnote", "endnote", "notes"]),
)
print(f"Found: {len(test3)}")

print("\n=== Test 4: Check if 'notes' is causing issues ===")
test4 = soup.find_all(
    ["div", "section", "aside"],
    class_=lambda x: x and any(marker in " ".join(x).lower() for marker in ["footnote", "endnote"]),
)
print(f"Found: {len(test4)}")

# Test the lambda on a known element
print("\n=== Manual test on known element ===")
known_div = soup.find("div", class_="single-article__footnotes-container")
if known_div:
    classes = known_div.get("class")
    print(f"Classes: {classes}")

    # Test each version of the lambda
    result1 = classes and "footnote" in " ".join(classes).lower()
    print(f"Test 1 result: {result1}")

    result2 = classes and any(marker in " ".join(classes).lower() for marker in ["footnote"])
    print(f"Test 2 result: {result2}")

    result3 = classes and any(
        marker in " ".join(classes).lower() for marker in ["footnote", "endnote", "notes"]
    )
    print(f"Test 3 result: {result3}")
