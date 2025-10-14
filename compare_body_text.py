#!/usr/bin/env python3
"""
Compare body text outputs across different experiment configurations.

Inspired by difflib usage in 12-factor-agents.
"""

import difflib
from pathlib import Path
from typing import Tuple, Dict
from dataclasses import dataclass


@dataclass
class DiffMetrics:
    """Metrics for comparing two text extractions."""

    similarity_ratio: float  # 0.0 to 1.0
    added_words: int
    removed_words: int
    changed_lines: int
    total_lines_a: int
    total_lines_b: int

    # Word-level statistics
    words_a: int
    words_b: int
    word_difference: int

    # Character-level
    chars_a: int
    chars_b: int
    char_difference: int


def compute_diff_metrics(text_a: str, text_b: str) -> DiffMetrics:
    """Compute comprehensive metrics comparing two text extractions."""

    # Overall similarity using SequenceMatcher
    matcher = difflib.SequenceMatcher(None, text_a, text_b)
    similarity = matcher.ratio()

    # Line-based comparison
    lines_a = text_a.splitlines()
    lines_b = text_b.splitlines()

    diff = list(difflib.unified_diff(lines_a, lines_b, lineterm=''))

    # Count additions and removals
    added_lines = sum(1 for line in diff if line.startswith('+') and not line.startswith('+++'))
    removed_lines = sum(1 for line in diff if line.startswith('-') and not line.startswith('---'))
    changed_lines = added_lines + removed_lines

    # Word counts
    words_a = len(text_a.split())
    words_b = len(text_b.split())
    word_diff = words_b - words_a

    # Get added/removed words
    # For simplicity, approximate from word counts
    added_words = max(0, word_diff)
    removed_words = max(0, -word_diff)

    # Character counts
    chars_a = len(text_a)
    chars_b = len(text_b)
    char_diff = chars_b - chars_a

    return DiffMetrics(
        similarity_ratio=similarity,
        added_words=added_words,
        removed_words=removed_words,
        changed_lines=changed_lines,
        total_lines_a=len(lines_a),
        total_lines_b=len(lines_b),
        words_a=words_a,
        words_b=words_b,
        word_difference=word_diff,
        chars_a=chars_a,
        chars_b=chars_b,
        char_difference=char_diff,
    )


def generate_unified_diff(text_a: str, text_b: str, label_a: str, label_b: str) -> str:
    """Generate unified diff format showing changes."""

    lines_a = text_a.splitlines(keepends=True)
    lines_b = text_b.splitlines(keepends=True)

    diff = difflib.unified_diff(
        lines_a,
        lines_b,
        fromfile=label_a,
        tofile=label_b,
        lineterm='',
    )

    return ''.join(diff)


def generate_html_diff(text_a: str, text_b: str, label_a: str, label_b: str) -> str:
    """Generate HTML side-by-side diff (useful for visual inspection)."""

    lines_a = text_a.splitlines()
    lines_b = text_b.splitlines()

    html_diff = difflib.HtmlDiff()
    return html_diff.make_file(
        lines_a,
        lines_b,
        fromdesc=label_a,
        todesc=label_b,
        context=True,
        numlines=3,
    )


def compare_experiments(
    doc_name: str,
    config_a: str,
    config_b: str,
    results_base_dir: Path = None,
) -> Tuple[DiffMetrics, str]:
    """
    Compare body text outputs from two different configurations.

    Args:
        doc_name: Document name (e.g., "Jackson_2014")
        config_a: First configuration name (e.g., "baseline")
        config_b: Second configuration name (e.g., "2x_scale")
        results_base_dir: Base directory for results (defaults to ./results)

    Returns:
        Tuple of (metrics, unified_diff_text)
    """

    if results_base_dir is None:
        results_base_dir = Path(__file__).parent / "results"

    # Load body text files
    path_a = results_base_dir / f"experiment_1" / f"{doc_name}_{config_a}_body.txt"
    path_b = results_base_dir / f"experiment_2" / f"{doc_name}_{config_b}_body.txt"

    if not path_a.exists():
        raise FileNotFoundError(f"File not found: {path_a}")
    if not path_b.exists():
        raise FileNotFoundError(f"File not found: {path_b}")

    text_a = path_a.read_text(encoding='utf-8')
    text_b = path_b.read_text(encoding='utf-8')

    # Compute metrics
    metrics = compute_diff_metrics(text_a, text_b)

    # Generate diff
    label_a = f"{doc_name} ({config_a})"
    label_b = f"{doc_name} ({config_b})"
    unified_diff = generate_unified_diff(text_a, text_b, label_a, label_b)

    return metrics, unified_diff


def generate_comparison_report(
    doc_name: str,
    configs: list[str],
    results_base_dir: Path = None,
) -> str:
    """Generate markdown report comparing multiple configurations for one document."""

    if results_base_dir is None:
        results_base_dir = Path(__file__).parent / "results"

    report = f"# Body Text Comparison: {doc_name}\n\n"
    report += "## Configuration Pairwise Comparisons\n\n"

    # Compare each pair
    for i, config_a in enumerate(configs):
        for config_b in configs[i+1:]:
            try:
                metrics, diff = compare_experiments(doc_name, config_a, config_b, results_base_dir)

                report += f"### {config_a} vs {config_b}\n\n"
                report += f"**Similarity**: {metrics.similarity_ratio:.1%}\n\n"
                report += f"| Metric | {config_a} | {config_b} | Difference |\n"
                report += f"|--------|----------|----------|------------|\n"
                report += f"| Words | {metrics.words_a:,} | {metrics.words_b:,} | {metrics.word_difference:+,} |\n"
                report += f"| Lines | {metrics.total_lines_a:,} | {metrics.total_lines_b:,} | {metrics.total_lines_b - metrics.total_lines_a:+,} |\n"
                report += f"| Characters | {metrics.chars_a:,} | {metrics.chars_b:,} | {metrics.char_difference:+,} |\n"

                report += f"\n**Changes**:\n"
                report += f"- Added: ~{metrics.added_words:,} words\n"
                report += f"- Removed: ~{metrics.removed_words:,} words\n"
                report += f"- Changed lines: {metrics.changed_lines:,}\n\n"

                # Only show diff preview if there are significant changes
                if metrics.similarity_ratio < 0.99:
                    diff_lines = diff.split('\n')
                    if len(diff_lines) > 10:
                        report += f"<details>\n<summary>Show diff preview (first 50 lines)</summary>\n\n```diff\n"
                        report += '\n'.join(diff_lines[:50])
                        report += f"\n... ({len(diff_lines) - 50} more lines)\n```\n</details>\n\n"
                    else:
                        report += f"<details>\n<summary>Show full diff</summary>\n\n```diff\n"
                        report += diff
                        report += "\n```\n</details>\n\n"
                else:
                    report += "*Outputs are >99% similar - negligible differences*\n\n"

            except FileNotFoundError as e:
                report += f"### {config_a} vs {config_b}\n\n"
                report += f"⚠️ Could not compare: {e}\n\n"

    return report


def main():
    """Interactive comparison tool."""

    import sys

    if len(sys.argv) < 4:
        print("Usage: python compare_body_text.py <doc_name> <config_a> <config_b>")
        print("\nExample:")
        print("  python compare_body_text.py Jackson_2014 baseline 2x_scale")
        print("\nOr generate full report:")
        print("  python compare_body_text.py Jackson_2014 --report baseline 2x_scale optimized")
        sys.exit(1)

    doc_name = sys.argv[1]

    if sys.argv[2] == "--report":
        # Generate full comparison report
        configs = sys.argv[3:]
        report = generate_comparison_report(doc_name, configs)

        output_path = Path(f"results/comparisons/{doc_name}_comparison.md")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report, encoding='utf-8')

        print(f"✅ Comparison report generated: {output_path}")
    else:
        # Compare two configs
        config_a = sys.argv[2]
        config_b = sys.argv[3]

        try:
            metrics, diff = compare_experiments(doc_name, config_a, config_b)

            print(f"\n{'='*80}")
            print(f"COMPARISON: {doc_name}")
            print(f"  {config_a} vs {config_b}")
            print(f"{'='*80}\n")

            print(f"Similarity: {metrics.similarity_ratio:.1%}")
            print(f"\n{config_a}:")
            print(f"  Words: {metrics.words_a:,}")
            print(f"  Lines: {metrics.total_lines_a:,}")
            print(f"  Chars: {metrics.chars_a:,}")

            print(f"\n{config_b}:")
            print(f"  Words: {metrics.words_b:,} ({metrics.word_difference:+,})")
            print(f"  Lines: {metrics.total_lines_b:,} ({metrics.total_lines_b - metrics.total_lines_a:+,})")
            print(f"  Chars: {metrics.chars_b:,} ({metrics.char_difference:+,})")

            print(f"\nChanges:")
            print(f"  Added: ~{metrics.added_words:,} words")
            print(f"  Removed: ~{metrics.removed_words:,} words")
            print(f"  Changed lines: {metrics.changed_lines:,}")

            # Save diff to file
            diff_path = Path(f"results/comparisons/{doc_name}_{config_a}_vs_{config_b}.diff")
            diff_path.parent.mkdir(parents=True, exist_ok=True)
            diff_path.write_text(diff, encoding='utf-8')

            print(f"\n📄 Full diff saved: {diff_path}")

        except FileNotFoundError as e:
            print(f"\n❌ Error: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
