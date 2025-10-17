#!/usr/bin/env python3
"""
Platform Cover Page Regex Patterns

This module defines regex patterns for detecting platform-added cover pages
from various academic databases and publishers.

These platform covers should be filtered out to obtain clean semantic/article
covers for ML training with DoclingBERT.

Usage:
    from platform_regex_patterns import PLATFORM_PATTERNS, detect_platform

    text = extract_text_from_pdf(pdf_path)
    platform, confidence = detect_platform(text)
"""

import re

# Platform-specific regex patterns
# Each platform has multiple patterns that indicate its presence
PLATFORM_PATTERNS = {
    "HeinOnline": {
        "description": "HeinOnline legal database platform covers",
        "example": "SOURCE: Content Downloaded from HeinOnline...",
        "patterns": [
            r"Downloaded from HeinOnline",
            r"SOURCE:\s*Content Downloaded from HeinOnline",
            r"DATE DOWNLOADED:\s+\w{3}\s+\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}\s+\d{4}",
            r"Bluebook\s+\d+\w+\s+ed\.",
            r"heinonline\.org",
            r"Citations:\s*Please note",  # HeinOnline citation header
        ],
        # Minimum patterns to match for high confidence
        "min_patterns_high_confidence": 2,
    },
    "Annual_Review": {
        "description": "Annual Reviews academic publisher platform covers",
        "example": "Downloaded from www.annualreviews.org. Guest (guest) IP: ...",
        "patterns": [
            r"Downloaded from www\.annualreviews\.org",
            r"annualreviews\.org",
            # Removed: r"Annual Review of \w+" - causes false positives (matches citations)
            r"Guest \(guest\) IP:",
            r"\(ar-\d+\)",  # Annual Reviews session identifier
            r"IP:\s+\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\s+On:",  # IP pattern
        ],
        "min_patterns_high_confidence": 2,
    },
    "JSTOR": {
        "description": "JSTOR digital library platform covers",
        "example": "JSTOR is a not-for-profit service... Stable URL: ...",
        "patterns": [
            r"\bJSTOR\b",  # Word boundaries to avoid substring matches
            r"www\.jstor\.org",
            r"Stable URL:",
            r"stable/\d+",
            r"jstor\.org/stable/",
            r"JSTOR is a not-for-profit",
        ],
        "min_patterns_high_confidence": 2,
    },
    "ProQuest": {
        "description": "ProQuest database platform covers",
        "example": "ProQuest document ID: ...",
        "patterns": [
            r"\bProQuest\b",  # Word boundaries to avoid substring matches
            # Removed: r"Dialog" - too generic, matches common words
            # Removed: r"UMI" - causes false positives (matches "Lumina", "illuminate", etc.)
            r"ProQuest document ID",
            r"proquest\.com",
        ],
        "min_patterns_high_confidence": 2,
    },
}


def detect_platform(text: str, verbose: bool = False) -> tuple[str | None, float]:
    """
    Detect which platform (if any) added a cover page to this PDF.

    Args:
        text: Text extracted from the PDF's first page
        verbose: If True, print debug information about pattern matches

    Returns:
        Tuple of (platform_name, confidence_score)
        - platform_name: Name of detected platform, or None if no platform detected
        - confidence: Float between 0.0 and 1.0 indicating detection confidence
          - 1.0 = High confidence (multiple patterns matched)
          - 0.5-0.9 = Medium confidence (some patterns matched)
          - 0.0 = No platform detected
    """
    platform_scores = {}

    for platform_name, platform_data in PLATFORM_PATTERNS.items():
        patterns = platform_data["patterns"]
        min_for_high_conf = platform_data["min_patterns_high_confidence"]

        # Count how many patterns match
        matches = 0
        matched_patterns = []

        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                matches += 1
                matched_patterns.append(pattern)

        if matches > 0:
            # Calculate confidence based on number of matches
            if matches >= min_for_high_conf:
                confidence = 1.0
            else:
                # Scale confidence between 0.5 and 0.9 for partial matches
                confidence = 0.5 + (0.4 * (matches / min_for_high_conf))

            platform_scores[platform_name] = {
                "confidence": confidence,
                "matches": matches,
                "matched_patterns": matched_patterns,
            }

            if verbose:
                print(f"\n{platform_name}:")
                print(f"  Matches: {matches}/{len(patterns)}")
                print(f"  Confidence: {confidence:.2f}")
                print(f"  Matched patterns: {matched_patterns}")

    # If no platforms detected
    if not platform_scores:
        return None, 0.0

    # Return platform with highest confidence
    best_platform = max(platform_scores.items(), key=lambda x: x[1]["confidence"])
    platform_name = best_platform[0]
    confidence = best_platform[1]["confidence"]

    return platform_name, confidence


def classify_cover(text: str) -> str:
    """
    Classify a cover page as either 'platform_cover' or 'semantic_cover'.

    Args:
        text: Text extracted from PDF's first page

    Returns:
        Classification: 'platform_cover' or 'semantic_cover'
    """
    # Only check first 1000 characters (where platform headers appear)
    # This avoids matching platform names in article body/citations
    search_text = text[:1000] if len(text) > 1000 else text

    platform, confidence = detect_platform(search_text)

    # Require higher confidence (0.9) to reduce false positives
    # This means at least 2 patterns must match for most platforms
    if platform and confidence >= 0.9:
        return "platform_cover"
    else:
        return "semantic_cover"


def get_platform_info(platform_name: str) -> dict:
    """
    Get detailed information about a specific platform.

    Args:
        platform_name: Name of the platform (e.g., 'HeinOnline')

    Returns:
        Dictionary with platform details, or empty dict if platform not found
    """
    return PLATFORM_PATTERNS.get(platform_name, {})


if __name__ == "__main__":
    # Example usage and testing
    print("Platform Regex Patterns Module")
    print("=" * 60)
    print(f"\nTotal platforms defined: {len(PLATFORM_PATTERNS)}")

    for platform_name, platform_data in PLATFORM_PATTERNS.items():
        print(f"\n{platform_name}:")
        print(f"  Description: {platform_data['description']}")
        print(f"  Patterns: {len(platform_data['patterns'])}")
        print(f"  Example: {platform_data['example'][:60]}...")

    # Test examples
    print("\n" + "=" * 60)
    print("Test Examples:")
    print("=" * 60)

    test_cases = [
        (
            "HeinOnline",
            "DATE DOWNLOADED: Sat Sep  6 15:21:46 2025\nSOURCE: Content Downloaded from HeinOnline\nCitations:\nBluebook 21st ed.",
        ),
        (
            "Annual Review",
            "Downloaded from www.annualreviews.org. Guest (guest) IP: 128.164.116.211 On: Tue, 14 Oct 2025",
        ),
        (
            "Semantic Cover (no platform)",
            "Toward a Radical Imagination of Law\nAmna A. Akbar\nNew York University Law Review",
        ),
    ]

    for test_name, test_text in test_cases:
        print(f"\nTest: {test_name}")
        platform, confidence = detect_platform(test_text, verbose=False)
        classification = classify_cover(test_text)
        print(f"  Detected: {platform if platform else 'None'}")
        print(f"  Confidence: {confidence:.2f}")
        print(f"  Classification: {classification}")
