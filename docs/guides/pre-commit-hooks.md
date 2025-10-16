# Pre-Commit Hooks for Documentation Validation

**Code Version:** 2.1.0
**Last Updated:** 2025-10-14

cite-assist uses pre-commit hooks to ensure documentation stays synchronized with code architecture.

## What Gets Validated

### Documentation Accuracy Hook (`validate-docs`)

Runs on every commit that touches:
- `README.md`
- `INTEGRATION_STATUS_FOR_PIN_CITER.md`
- `docs/**/*.md`
- `core/api/**/*.py`
- `api/pin_citer_api.py`

### Checks Performed

1. **README.md Accuracy**
   - ✅ Doesn't claim "CLI-only" (we have FastAPI server)
   - ✅ Mentions integration options (CLI + HTTP API)
   - ✅ Documents correct service ports:
     - `localhost:8000` - FastAPI server
     - `localhost:8080` - Embedding service
     - `localhost:6333` - Qdrant vector database

2. **API Documentation Completeness**
   - ✅ `docs/pin-citer/api.md` exists
   - ✅ Documents key endpoints: `/api/search`, `/api/search/sentences`, `/health`

3. **Integration Status**
   - ✅ Mentions both direct Python import and HTTP API
   - ✅ Explains why PIN-CITER uses direct import

4. **Code Reality Check**
   - ✅ FastAPI app exists at `core/api/main.py`
   - ✅ Search endpoints exist at `core/api/search.py`
   - ✅ Documented features match actual code

## Installation

Pre-commit hooks are already configured. To install:

```bash
# Install pre-commit (if not already installed)
pip install pre-commit

# Install git hooks
pre-commit install

# Test hooks on all files
pre-commit run --all-files
```

## Usage

### Automatic (Recommended)

Hooks run automatically on `git commit`:

```bash
git add README.md
git commit -m "Update README"

# Output:
# Validate Documentation Accuracy..................Passed
# Generate API Documentation........................Passed
```

### Manual

Run hooks manually anytime:

```bash
# Run all hooks
pre-commit run --all-files

# Run specific hook
pre-commit run validate-docs --all-files
pre-commit run generate-docs --all-files
```

## What Happens on Commit

### Success Flow

```bash
$ git commit -m "Update API endpoint"

Validate Documentation Accuracy..................Passed
Generate API Documentation........................Passed
ruff................................................Passed
ruff-format........................................Passed
check-yaml.........................................Passed
[main abc1234] Update API endpoint
```

### Failure Flow

```bash
$ git commit -m "Update README"

Validate Documentation Accuracy..................Failed
- hook id: validate-docs
- exit code: 1

❌ ERRORS (1):

1. README.md contains outdated claim: 'CLI-only tool'
   Reality: FastAPI server runs on localhost:8000
   Fix: Update README to mention both CLI and HTTP API

# Commit blocked - fix issues and retry
```

## Common Scenarios

### Scenario 1: Adding New API Endpoint

When you add a new endpoint to `core/api/search.py`:

1. Write endpoint with docstring
2. Commit changes
3. `generate-docs` hook auto-generates markdown docs
4. `validate-docs` ensures consistency

### Scenario 2: Updating README

When you update architecture in README:

1. Edit README.md
2. Commit changes
3. `validate-docs` checks for common inaccuracies:
   - "CLI-only" claims
   - Incorrect port numbers
   - Missing integration methods

### Scenario 3: Refactoring API Structure

When you move/rename API modules:

1. Update code
2. Update relevant markdown docs
3. Commit together
4. Hooks verify consistency

## Bypassing Hooks (Emergency Only)

**Not recommended**, but if absolutely necessary:

```bash
# Skip all hooks
git commit --no-verify -m "Emergency fix"

# Skip specific hook
SKIP=validate-docs git commit -m "Temporary"
```

**Important:** Never bypass hooks for regular commits. They prevent documentation drift.

## Hook Configuration

Location: `.pre-commit-config.yaml`

```yaml
- repo: local
  hooks:
    - id: validate-docs
      name: Validate Documentation Accuracy
      entry: python3 scripts/validate_docs.py
      language: system
      files: '^(README\.md|INTEGRATION_STATUS.*\.md|docs/.*\.md|core/api/.*\.py|api/pin_citer_api\.py)$'
      pass_filenames: false
      stages: [pre-commit]

    - id: generate-docs
      name: Generate API Documentation
      entry: python3 scripts/generate_docs.py
      language: system
      files: '^(core/api/.*\.py|api/pin_citer_api\.py)$'
      pass_filenames: false
      stages: [pre-commit]
```

## Troubleshooting

### Hook Failed: "Module not found"

```bash
# Ensure dependencies installed
uv sync

# Retry
pre-commit run --all-files
```

### Hook Failed: "FastAPI app not found"

Check that `core/api/main.py` exists and defines `app`:

```python
from fastapi import FastAPI

app = FastAPI(title="Cite-Assist API", ...)
```

### Hook Passed But Docs Still Wrong

Hooks check for **common** issues. Manual review still required:

```bash
# Review generated docs
ls -la docs/api/

# Check README sections
grep -A 10 "Integration Options" README.md
```

### False Positive Warnings

If validator warns about something that's intentionally different:

1. Review the warning
2. If incorrect, update `scripts/validate_docs.py` logic
3. Commit updated validator with explanation

## Best Practices

### 1. Write Comprehensive Docstrings

```python
async def search_for_pin_citer(
    query: str,
    library_id: int,
    top_k: int = 10
) -> Dict[str, Any]:
    """Search for citations with Zotero metadata.

    Args:
        query: Search text
        library_id: Zotero library ID
        top_k: Maximum results

    Returns:
        Dict with 'results', 'count', 'library_id'

    Example:
        >>> result = await search_for_pin_citer("legal text", 5673253)
        >>> print(result['count'])
        5
    """
```

### 2. Update Docs Atomically

Commit code + doc changes together:

```bash
# Good
git add core/api/search.py docs/pin-citer/api.md
git commit -m "Add /api/search endpoint"

# Bad (docs lag behind)
git add core/api/search.py
git commit -m "Add endpoint"
# ... later (docs out of date)
git add docs/pin-citer/api.md
git commit -m "Update docs"
```

### 3. Test Docs Locally

Before committing:

```bash
# Validate
python3 scripts/validate_docs.py

# Generate
python3 scripts/generate_docs.py

# Review generated output
cat docs/api/search.md
```

## Related Documentation

- [README.md](../../README.md) - Integration options
- [docs/pin-citer/api.md](../pin-citer/api.md) - HTTP API reference
- [INTEGRATION_STATUS_FOR_PIN_CITER.md](../../INTEGRATION_STATUS_FOR_PIN_CITER.md) - Current integration

---

**Last Updated:** 2025-10-09
**Hook Version:** 1.0.0
