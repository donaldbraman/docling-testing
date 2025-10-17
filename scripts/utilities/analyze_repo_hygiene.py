#!/usr/bin/env python3
"""
Repository Hygiene Analyzer
Analyzes collection logs, docs, and data for staleness and organization issues
"""

from collections import defaultdict
from datetime import datetime
from pathlib import Path

# Paths
REPO_ROOT = Path("/Users/donaldbraman/Documents/GitHub/docling-testing")
COLLECTION_LOGS_DIR = REPO_ROOT / "data/collection_logs"
RAW_PDF_DIR = REPO_ROOT / "data/raw_pdf"
DOCS_DIR = REPO_ROOT / "docs"
SCRIPTS_DIR = REPO_ROOT / "scripts"


def analyze_collection_logs():
    """Analyze collection log directories for usage and staleness"""
    print("=" * 80)
    print("COLLECTION LOGS ANALYSIS")
    print("=" * 80)

    log_dirs = sorted(COLLECTION_LOGS_DIR.iterdir())

    active_logs = []
    empty_logs = []
    stale_logs = []

    for log_dir in log_dirs:
        if not log_dir.is_dir():
            continue

        # Count files in log directory
        log_files = list(log_dir.iterdir())
        file_count = len(log_files)

        # Count corresponding PDFs
        source_name = log_dir.name
        pdf_pattern = f"{source_name}_*.pdf"
        pdf_count = len(list(RAW_PDF_DIR.glob(pdf_pattern)))

        # Check modification time
        mtime = datetime.fromtimestamp(log_dir.stat().st_mtime)
        age_days = (datetime.now() - mtime).days

        status = {
            "name": source_name,
            "log_files": file_count,
            "pdf_count": pdf_count,
            "age_days": age_days,
            "last_modified": mtime.strftime("%Y-%m-%d"),
        }

        if pdf_count > 0:
            active_logs.append(status)
        elif file_count == 0:
            empty_logs.append(status)
        else:
            stale_logs.append(status)

    print(f"\nTotal collection log directories: {len(log_dirs)}")
    print(f"  Active (with PDFs): {len(active_logs)}")
    print(f"  Stale (logs but no PDFs): {len(stale_logs)}")
    print(f"  Empty (no files): {len(empty_logs)}")

    if active_logs:
        print(f"\n{'Active Logs':-^80}")
        for log in active_logs:
            print(
                f"  {log['name']:<40} {log['pdf_count']:>3} PDFs | {log['log_files']:>2} logs | {log['last_modified']}"
            )

    if stale_logs:
        print(f"\n{'Stale Logs (logs but no PDFs)':-^80}")
        for log in stale_logs:
            print(
                f"  {log['name']:<40} {log['log_files']:>2} logs | {log['last_modified']} ({log['age_days']} days old)"
            )

    if empty_logs:
        print(f"\n{'Empty Logs':-^80}")
        for log in empty_logs:
            print(f"  {log['name']:<40} (empty directory)")

    return {"active": active_logs, "stale": stale_logs, "empty": empty_logs}


def analyze_docs():
    """Analyze documentation for staleness"""
    print("\n" + "=" * 80)
    print("DOCUMENTATION ANALYSIS")
    print("=" * 80)

    docs = sorted(DOCS_DIR.glob("**/*.md"))

    recent_docs = []
    old_docs = []

    for doc in docs:
        mtime = datetime.fromtimestamp(doc.stat().st_mtime)
        age_days = (datetime.now() - mtime).days

        status = {
            "name": doc.relative_to(REPO_ROOT),
            "age_days": age_days,
            "last_modified": mtime.strftime("%Y-%m-%d"),
            "size_kb": doc.stat().st_size / 1024,
        }

        if age_days <= 1:
            recent_docs.append(status)
        else:
            old_docs.append(status)

    print(f"\nTotal documentation files: {len(docs)}")
    print(f"  Recent (≤1 day): {len(recent_docs)}")
    print(f"  Older (>1 day): {len(old_docs)}")

    if recent_docs:
        print(f"\n{'Recent Documentation':-^80}")
        for doc in recent_docs:
            print(f"  {str(doc['name']):<50} {doc['last_modified']} ({doc['size_kb']:.1f} KB)")

    if old_docs:
        print(f"\n{'Older Documentation (may need review)':-^80}")
        for doc in sorted(old_docs, key=lambda x: x["age_days"], reverse=True)[:10]:
            print(f"  {str(doc['name']):<50} {doc['last_modified']} ({doc['age_days']} days old)")

    return {"recent": recent_docs, "old": old_docs}


def analyze_test_data():
    """Analyze test data directories"""
    print("\n" + "=" * 80)
    print("TEST DATA ANALYSIS")
    print("=" * 80)

    # Check for test directories
    test_dirs = [
        REPO_ROOT / "data/cover_pages/test_sample",
        REPO_ROOT / "data/cover_pages/verified_covers/source_pdfs_cover_page_only",
    ]

    for test_dir in test_dirs:
        if test_dir.exists():
            file_count = len(list(test_dir.iterdir()))
            size_mb = sum(f.stat().st_size for f in test_dir.rglob("*") if f.is_file()) / (
                1024 * 1024
            )
            print(f"\n  {test_dir.relative_to(REPO_ROOT)}")
            print(f"    Files: {file_count}")
            print(f"    Size: {size_mb:.1f} MB")
            print("    Recommendation: Review if still needed or archive")


def analyze_scripts():
    """Analyze scripts for duplicates and organization"""
    print("\n" + "=" * 80)
    print("SCRIPTS ANALYSIS")
    print("=" * 80)

    script_dirs = defaultdict(list)

    for script in SCRIPTS_DIR.rglob("*.py"):
        subdir = script.parent.name
        script_dirs[subdir].append(script.name)

    print("\nScript organization:")
    for subdir in sorted(script_dirs.keys()):
        print(f"  {subdir}/: {len(script_dirs[subdir])} scripts")

    # Check for collection scripts
    collection_scripts = list((SCRIPTS_DIR / "data_collection").glob("collect_*.py"))
    scrape_scripts = list((SCRIPTS_DIR / "data_collection").glob("scrape_*.py"))

    print("\n  Data collection scripts:")
    print(f"    collect_* scripts: {len(collection_scripts)}")
    print(f"    scrape_* scripts: {len(scrape_scripts)}")


def main():
    print("\n")
    print("=" * 80)
    print(" REPOSITORY HYGIENE ANALYSIS")
    print("=" * 80)
    print()

    # Analyze collection logs
    log_analysis = analyze_collection_logs()

    # Analyze documentation
    doc_analysis = analyze_docs()

    # Analyze test data
    analyze_test_data()

    # Analyze scripts
    analyze_scripts()

    # Summary recommendations
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)

    print("\n1. COLLECTION LOGS:")
    if log_analysis["empty"]:
        print(f"   - Remove {len(log_analysis['empty'])} empty log directories")
    if log_analysis["stale"]:
        print(f"   - Review {len(log_analysis['stale'])} stale log directories (logs but no PDFs)")
        print("   - Consider archiving or removing if collection failed/abandoned")

    print("\n2. DOCUMENTATION:")
    print(f"   - {len(doc_analysis['recent'])} recent docs (review for git commit)")
    print(f"   - {len(doc_analysis['old'])} older docs (review for staleness)")

    print("\n3. GIT TRACKING:")
    print("   - Untracked files to review:")
    print("     • data/collection_logs/arxiv/ - COMMIT (active collection)")
    print("     • data/collection_logs/pubmed_central/ - REVIEW (failed collection, may delete)")
    print("     • docs/CORPUS_PLATFORM_COVER_CLEANING_REPORT.md - COMMIT (important report)")
    print("     • docs/NON_LAW_COLLECTION_DEPLOYMENT_SUMMARY.md - COMMIT (important report)")

    print("\n4. CLEANUP:")
    print("   - Test directories: Review data/cover_pages/test_sample/")
    print("   - Corrupted PDF: Remove bu_law_review_online_harassment_intermediary_immunity.pdf")

    print("\n" + "=" * 80)
    print()


if __name__ == "__main__":
    main()
