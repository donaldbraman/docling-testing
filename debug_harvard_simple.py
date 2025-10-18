#!/usr/bin/env python3
"""Simple debug of BeautifulSoup class matching."""

from pathlib import Path

from bs4 import BeautifulSoup

html_file = Path("data/v3_data/raw_html/harvard_law_review_excited_delirium.html")

with open(html_file, encoding="utf-8") as f:
    soup = BeautifulSoup(f.read(), "html.parser")

print("=== Test 1: Find div with exact class name ===")
test1 = soup.find_all("div", class_="single-article__footnotes-container")
print(f"Found: {len(test1)}")

print("\n=== Test 2: Find div with class containing string ===")
test2 = soup.find_all("div", class_=lambda x: "footnotes-container" in str(x) if x else False)
print(f"Found: {len(test2)}")

print("\n=== Test 3: Manual iteration (original working method) ===")
count = 0
for div in soup.find_all("div"):
    classes = div.get("class")
    if classes and "footnote" in " ".join(classes).lower():
        count += 1
print(f"Found: {count}")

print("\n=== Test 4: The problematic lambda ===")
test4 = soup.find_all(
    ["div", "section", "aside"],
    class_=lambda x: x
    and any(marker in " ".join(x).lower() for marker in ["footnote", "endnote", "notes"]),
)
print(f"Found: {len(test4)}")
