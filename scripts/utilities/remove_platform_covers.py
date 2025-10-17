#!/usr/bin/env python3
"""
Simple Platform Cover Page Detector and Remover

This utility detects and removes platform-added cover pages from PDFs
to obtain clean article content for ML training.

Usage:
    # Process single PDF
    python remove_platform_covers.py input.pdf output.pdf

    # Process directory of PDFs
    python remove_platform_covers.py --dir data/raw_pdf --output data/clean_pdf

    # Check PDF without removing cover
    python remove_platform_covers.py --check input.pdf
"""

import argparse
import sys
from pathlib import Path

try:
    import pypdf
except ImportError:
    print("Error: pypdf not installed. Run: pip install pypdf")
    sys.exit(1)

# Add scripts/testing to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "testing"))

try:
    from platform_regex_patterns import detect_platform
except ImportError:
    print("Error: platform_regex_patterns.py not found")
    print("Expected location: scripts/testing/platform_regex_patterns.py")
    sys.exit(1)


def check_platform_cover(pdf_path: Path) -> tuple[bool, str, float]:
    """
    Check if PDF has a platform-added cover page.

    Args:
        pdf_path: Path to PDF file

    Returns:
        Tuple of (has_platform_cover, platform_name, confidence)
    """
    try:
        with open(pdf_path, "rb") as f:
            reader = pypdf.PdfReader(f)

            if len(reader.pages) == 0:
                return False, "empty_pdf", 0.0

            # Extract first page text
            first_page_text = reader.pages[0].extract_text()

            # Detect platform
            platform, confidence = detect_platform(first_page_text[:1000])

            has_platform = platform is not None and confidence >= 0.9

            return has_platform, platform or "none", confidence

    except Exception as e:
        print(f"Error reading {pdf_path}: {e}")
        return False, "error", 0.0


def remove_platform_cover(input_pdf: Path, output_pdf: Path) -> bool:
    """
    Remove first page from PDF if it's a platform cover.

    Args:
        input_pdf: Input PDF path
        output_pdf: Output PDF path (without cover page)

    Returns:
        True if cover was removed, False otherwise
    """
    has_platform, platform_name, confidence = check_platform_cover(input_pdf)

    if not has_platform:
        print(f"No platform cover detected in {input_pdf.name}")
        return False

    try:
        # Read PDF
        with open(input_pdf, "rb") as f:
            reader = pypdf.PdfReader(f)
            writer = pypdf.PdfWriter()

            # Copy all pages except first (platform cover)
            for page_num in range(1, len(reader.pages)):
                writer.add_page(reader.pages[page_num])

            # Write output
            with open(output_pdf, "wb") as out_f:
                writer.write(out_f)

        print(f"✓ Removed {platform_name} cover from {input_pdf.name}")
        print(f"  Output: {output_pdf}")
        print(f"  Confidence: {confidence:.2f}")
        return True

    except Exception as e:
        print(f"Error removing cover from {input_pdf}: {e}")
        return False


def process_directory(input_dir: Path, output_dir: Path, dry_run: bool = False):
    """
    Process all PDFs in a directory.

    Args:
        input_dir: Directory containing PDFs
        output_dir: Output directory for cleaned PDFs
        dry_run: If True, only check for platform covers without removing
    """
    if not input_dir.exists():
        print(f"Error: Input directory not found: {input_dir}")
        return

    # Create output directory
    if not dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)

    # Find all PDFs
    pdf_files = list(input_dir.glob("*.pdf"))

    if not pdf_files:
        print(f"No PDF files found in {input_dir}")
        return

    print(f"Processing {len(pdf_files)} PDFs from {input_dir}")
    print("=" * 80)

    platform_count = 0
    semantic_count = 0
    error_count = 0

    for pdf_file in pdf_files:
        has_platform, platform_name, confidence = check_platform_cover(pdf_file)

        if has_platform:
            platform_count += 1
            print(f"\n[PLATFORM] {pdf_file.name}")
            print(f"  Platform: {platform_name} (confidence: {confidence:.2f})")

            if not dry_run:
                output_file = output_dir / pdf_file.name
                remove_platform_cover(pdf_file, output_file)
        else:
            semantic_count += 1
            if not dry_run:
                # Copy file as-is
                import shutil

                output_file = output_dir / pdf_file.name
                shutil.copy2(pdf_file, output_file)

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total PDFs: {len(pdf_files)}")
    print(
        f"Platform covers detected: {platform_count} ({100 * platform_count / len(pdf_files):.1f}%)"
    )
    print(f"Semantic covers: {semantic_count} ({100 * semantic_count / len(pdf_files):.1f}%)")
    print(f"Errors: {error_count}")

    if dry_run:
        print("\nDry run complete. No files were modified.")
    else:
        print(f"\nOutput directory: {output_dir}")


def main():
    parser = argparse.ArgumentParser(
        description="Detect and remove platform-added cover pages from PDFs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check single PDF
  python remove_platform_covers.py --check input.pdf

  # Remove cover from single PDF
  python remove_platform_covers.py input.pdf output.pdf

  # Process directory (dry run)
  python remove_platform_covers.py --dir data/raw_pdf --dry-run

  # Process directory and save cleaned PDFs
  python remove_platform_covers.py --dir data/raw_pdf --output data/clean_pdf
        """,
    )

    parser.add_argument("input_pdf", nargs="?", type=Path, help="Input PDF file")
    parser.add_argument("output_pdf", nargs="?", type=Path, help="Output PDF file (without cover)")

    parser.add_argument("--dir", type=Path, help="Process all PDFs in this directory")
    parser.add_argument("--output", type=Path, help="Output directory for cleaned PDFs")
    parser.add_argument(
        "--check", action="store_true", help="Only check for platform covers, don't remove"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Check all PDFs but don't remove covers"
    )

    args = parser.parse_args()

    # Validate arguments
    if args.dir:
        # Directory mode
        if not args.output and not args.dry_run:
            print("Error: --output required when using --dir (or use --dry-run)")
            sys.exit(1)

        process_directory(args.dir, args.output or Path("output"), args.dry_run)

    elif args.input_pdf:
        # Single file mode
        if args.check:
            # Check only
            has_platform, platform_name, confidence = check_platform_cover(args.input_pdf)

            print(f"File: {args.input_pdf}")
            if has_platform:
                print(f"✓ Platform cover detected: {platform_name} (confidence: {confidence:.2f})")
                print("  Recommendation: Remove first page before using for training")
            else:
                print("✓ No platform cover detected")
                print("  This PDF can be used directly for training")

        elif args.output_pdf:
            # Remove cover
            removed = remove_platform_cover(args.input_pdf, args.output_pdf)
            if not removed:
                # No cover detected, copy file as-is
                import shutil

                shutil.copy2(args.input_pdf, args.output_pdf)
                print(f"Copied {args.input_pdf} to {args.output_pdf} (no changes)")
        else:
            print("Error: output_pdf required (or use --check)")
            sys.exit(1)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
