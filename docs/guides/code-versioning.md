# Code and Documentation Versioning Strategy

**Code Version:** 2.1.1
**Last Updated:** 2025-10-14
**Status:** Production Policy

## Overview

Cite-assist uses semantic versioning for both code and documentation to ensure guides stay synchronized with the codebase. This document defines our versioning strategy and how to maintain version compatibility.

## Table of Contents

- [Version Format](#version-format)
- [Code Versioning](#code-versioning)
- [Documentation Versioning](#documentation-versioning)
- [Version Checking](#version-checking)
- [When to Increment Versions](#when-to-increment-versions)
- [Guide Metadata Format](#guide-metadata-format)
- [Maintenance Workflow](#maintenance-workflow)

---

## Version Format

We use **Semantic Versioning 2.0.0** for the codebase:

```
MAJOR.MINOR.PATCH
```

**Example:** `2.1.0`
- **MAJOR**: 2 (v2 API with CSL-JSON compliance)
- **MINOR**: 1 (Added version tracking, removed full_text_embeddings)
- **PATCH**: 0 (No bug fixes since last minor)

---

## Code Versioning

### Current Version Location

The canonical version is stored in:
```
/VERSION
```

Contains a single line with the version number:
```
2.1.0
```

### Reading Version in Code

```python
from pathlib import Path

def get_version() -> str:
    """Get current code version."""
    version_file = Path(__file__).parent.parent / "VERSION"
    return version_file.read_text().strip()
```

### Version History

| Version | Date | Changes |
|---------|------|---------|
| **2.1.0** | 2025-10-14 | Version tracking (Issue #432), removed full_text_embeddings (Issue #434), guide versioning system |
| **2.0.0** | 2025-10-10 | v2 API with CSL-JSON compliance, batch search endpoint |
| **1.0.0** | 2025-09-01 | Initial production release with v1 API |

---

## Documentation Versioning

### Guide Metadata

Every guide must include version metadata in its header:

```markdown
# Guide Title

**Code Version:** 2.1.0
**Last Updated:** 2025-10-14
**Status:** Production Guide

## Content...
```

**Required fields:**
- `Code Version`: Version of codebase this guide documents
- `Last Updated`: Date guide was last reviewed/updated
- `Status`: Production Guide | Draft | Deprecated

### Version Compatibility

**Version matching rules:**

1. **MAJOR must match** - Guide for 2.x.x won't work for 1.x.x code
2. **MINOR can differ by ±1** - Guide for 2.1.0 is OK for code 2.0.0 or 2.2.0
3. **PATCH doesn't matter** - Guide for 2.1.0 works for code 2.1.5

**Examples:**
```
Code 2.1.0 ✅ Guide 2.1.0 (exact match)
Code 2.1.0 ✅ Guide 2.0.0 (minor -1)
Code 2.1.0 ✅ Guide 2.2.0 (minor +1)
Code 2.1.0 ⚠️  Guide 2.3.0 (minor +2, may be outdated)
Code 2.1.0 ❌ Guide 1.5.0 (major mismatch)
Code 3.0.0 ❌ Guide 2.1.0 (major mismatch)
```

---

## Version Checking

### Automated Validation

Use `validate_guides.py` to check version compatibility:

```bash
# Check all guides for version compatibility
uv run python scripts/validate_guides.py --check-versions

# Verbose output shows mismatches
uv run python scripts/validate_guides.py --check-versions --verbose
```

**Output example:**
```
Guide Validation Results
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Guide                    Code Ver  Compatible
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
pipeline-scripts.md      2.1.0     ✅
embedding-service.md     2.1.0     ✅
qdrant-sync.md           2.0.0     ⚠️ (minor behind)
api-versioning.md        2.1.0     ✅
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ 1 guide(s) may need review
```

### Pre-Commit Hook

Version checking is integrated into pre-commit hooks:

```yaml
# .pre-commit-config.yaml
- id: validate-guides
  name: Validate Guide Links and Versions
  entry: uv run python scripts/validate_guides.py --check-versions
```

---

## When to Increment Versions

### MAJOR Version (X.0.0)

Increment when making **breaking changes**:

**Code changes:**
- New API major version (v2 → v3)
- Removing core collections (like removing text_chunks)
- Changing core pipeline architecture
- Removing required features

**Documentation impact:** All guides need review and updates

**Example:** `2.1.0 → 3.0.0`
```bash
echo "3.0.0" > VERSION
# Update all guides with new version
# Update CHANGELOG.md
```

### MINOR Version (x.Y.0)

Increment when adding **new features** (backward compatible):

**Code changes:**
- Adding new API endpoints
- Adding new collections
- New optional features
- Adding new scripts or utilities

**Documentation impact:** Affected guides need updates, others remain compatible

**Example:** `2.1.0 → 2.2.0`
```bash
echo "2.2.0" > VERSION
# Update only affected guides
```

### PATCH Version (x.x.Z)

Increment for **bug fixes** and minor updates:

**Code changes:**
- Bug fixes
- Performance improvements
- Documentation-only changes
- Refactoring without behavior changes

**Documentation impact:** Minimal, guides remain compatible

**Example:** `2.1.0 → 2.1.1`
```bash
echo "2.1.1" > VERSION
# Update CHANGELOG.md only
```

---

## Guide Metadata Format

### Standard Header Template

```markdown
# [Guide Title]

**Code Version:** 2.1.0
**Last Updated:** 2025-10-14
**Status:** Production Guide

## Overview

[Guide content...]
```

### Status Values

| Status | Meaning |
|--------|---------|
| **Production Guide** | Current, tested, accurate for production code |
| **Draft** | In development, may be incomplete |
| **Deprecated** | Superseded by newer guide or outdated |

### Example Metadata Block

```markdown
# Pipeline Scripts Guide

**Code Version:** 2.1.0
**Last Updated:** 2025-10-14
**Status:** Production Guide

## Overview

This guide covers all production pipeline scripts...
```

---

## Maintenance Workflow

### When Code Changes (Developer)

**MAJOR or MINOR version increment:**

1. **Update VERSION file:**
   ```bash
   echo "2.2.0" > VERSION
   ```

2. **Identify affected guides:**
   ```bash
   # List guides that may need updates
   grep -r "Code Version: 2\." docs/guides/ | cut -d: -f1 | sort -u
   ```

3. **Review and update guides:**
   - Update guide content for new features
   - Update `Code Version:` to new version
   - Update `Last Updated:` to current date

4. **Validate:**
   ```bash
   uv run python scripts/validate_guides.py --check-versions --verbose
   ```

5. **Commit together:**
   ```bash
   git add VERSION docs/guides/
   git commit -m "feat: Increment version to 2.2.0 and update affected guides"
   ```

**PATCH version increment:**

1. Update VERSION file
2. Update CHANGELOG.md
3. No guide updates needed (unless doc-only changes)

### When Guides Updated (Writer)

1. **Update guide content**

2. **Update metadata:**
   ```markdown
   **Code Version:** 2.1.0  # Match current VERSION file
   **Last Updated:** 2025-10-14  # Today's date
   ```

3. **Validate:**
   ```bash
   uv run python scripts/validate_guides.py --check-versions
   ```

4. **Commit:**
   ```bash
   git add docs/guides/[guide-name].md
   git commit -m "docs: Update [guide-name] for accuracy"
   ```

### Periodic Maintenance

**Monthly review:**

```bash
# Check for outdated guides
uv run python scripts/validate_guides.py --check-versions --verbose

# Review guides with version warnings
# Update or mark as deprecated
```

---

## Integration with API Versioning

### Relationship

- **Code versions** (2.1.0): Entire codebase version
- **API versions** (v1, v2, v3): Public API interface version

**Example:**
```
Code Version 2.1.0 includes:
- API v2 (production)
- API v1 (deprecated)

Code Version 3.0.0 might include:
- API v3 (production)
- API v2 (supported)
- API v1 (removed)
```

### When API Version Changes

**New API version (v2 → v3):**
- Increment code MAJOR version: `2.x.x → 3.0.0`
- Update all affected guides
- See [api-versioning.md](api-versioning.md) for API-specific deprecation policy

---

## Changelog

Maintain a CHANGELOG.md at project root documenting all version changes:

```markdown
# Changelog

## [2.1.0] - 2025-10-14
### Added
- Version tracking for chunks and embeddings (Issue #432)
- Code and documentation versioning system

### Removed
- full_text_embeddings collection (Issue #434)

## [2.0.0] - 2025-10-10
### Added
- v2 API with CSL-JSON compliance
- Batch search endpoint

### Changed
- Response format now CSL-compliant

## [1.0.0] - 2025-09-01
### Added
- Initial production release
- v1 API with basic search
```

---

## Best Practices

### 1. Version on Breaking Changes

**When in doubt:** If unsure whether a change is breaking, increment MINOR version and document carefully.

### 2. Update Guides Atomically

**Good:**
```bash
# Code change + guide update in same commit
git add core/api/search.py docs/guides/pin-citer-integration.md VERSION
git commit -m "feat: Add new endpoint and update guide to version 2.2.0"
```

**Bad:**
```bash
# Code change without guide update
git add core/api/search.py
git commit -m "feat: Add new endpoint"
# (Guide now outdated!)
```

### 3. Use Pre-Commit Hooks

**Enable version checking:**
```bash
pre-commit install
# Now version mismatches block commits
```

### 4. Review Quarterly

**Schedule:** Every 3 months, audit all guides
- Check version compatibility
- Update outdated guides
- Mark deprecated guides

---

## Related Documentation

- [API Versioning Strategy](api-versioning.md) - API-specific versioning
- [Guide Validation](../scripts/validate_guides.py) - Automated checking
- [Pre-Commit Hooks](pre-commit-hooks.md) - Automated validation

---

## References

- [Semantic Versioning 2.0.0](https://semver.org/)
- [Keep a Changelog](https://keepachangelog.com/)
- [Documentation as Code](https://www.writethedocs.org/guide/docs-as-code/)

---

*This versioning system ensures documentation stays synchronized with code, reducing maintenance burden and improving accuracy.*
