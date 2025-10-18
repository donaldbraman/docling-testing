#!/usr/bin/env python3
"""Debug Harvard Law Review extraction."""

from pathlib import Path

from bs4 import BeautifulSoup

html_file = Path("data/v3_data/raw_html/harvard_law_review_excited_delirium.html")

with open(html_file, encoding="utf-8") as f:
    soup = BeautifulSoup(f.read(), "html.parser")

# Test BEFORE removing script/style
print("=== BEFORE decomposing script/style ===")
footnote_sections_before = soup.find_all(
    ["div", "section", "aside"],
    class_=lambda x: x
    and any(marker in " ".join(x).lower() for marker in ["footnote", "endnote", "notes"]),
)
print(f"Sections found: {len(footnote_sections_before)}")

# Remove script and style
for script in soup(["script", "style"]):
    script.decompose()

print("\n=== AFTER decomposing script/style ===")
footnote_sections_after = soup.find_all(
    ["div", "section", "aside"],
    class_=lambda x: x
    and any(marker in " ".join(x).lower() for marker in ["footnote", "endnote", "notes"]),
)
print(f"Sections found: {len(footnote_sections_after)}")

# Find ALL divs with "footnote" in class name
print("=== Searching for divs with 'footnote' in class ===")
all_divs = soup.find_all("div")
print(f"Total divs: {len(all_divs)}")

for div in all_divs:
    classes = div.get("class")
    if classes:
        class_str = " ".join(classes)
        if "footnote" in class_str.lower():
            print("\nFound div with footnote:")
            print(f"  Classes: {classes}")
            print(f"  Joined: '{class_str}'")
            print(f"  Lowercase: '{class_str.lower()}'")
            print(f"  Contains 'footnote': {'footnote' in class_str.lower()}")

            # Count paragraphs
            paragraphs = div.find_all("p")
            print(f"  Paragraphs in this div: {len(paragraphs)}")

print("\n\n=== Testing the actual lambda function ===")

# Test the lambda on the main footnote container
main_container = soup.find("div", class_="single-article__footnotes-container")
if main_container:
    classes = main_container.get("class")
    print(f"Main container classes: {classes}")
    print(f"Type: {type(classes)}")

    # Test the lambda logic manually
    if classes:
        joined = " ".join(classes).lower()
        print(f"Joined lowercase: '{joined}'")
        has_footnote = "footnote" in joined
        print(f"Contains 'footnote': {has_footnote}")

        # Test what the lambda returns
        lambda_func = lambda x: x and any(
            marker in " ".join(x).lower() for marker in ["footnote", "endnote", "notes"]
        )
        result = lambda_func(classes)
        print(f"Lambda returns: {result}")

print("\n=== Now call find_all with lambda ===")
footnote_sections = soup.find_all(
    ["div", "section", "aside"],
    class_=lambda x: x
    and any(marker in " ".join(x).lower() for marker in ["footnote", "endnote", "notes"]),
)
print(f"Sections found by lambda: {len(footnote_sections)}")
