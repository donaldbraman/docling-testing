# Testing Workflow

**Code Version:** 2.1.2
**Last Updated:** 2025-10-14

## Purpose

Autonomous test execution without context pollution. Agents run tests independently and report only failures/warnings.

## Test Library

**Prosecutors Paradox**: 5673253 (Zotero group library)

All tests use real data. No mocks.

## Test Suites

### Unit Tests

**Command:**
```bash
uv run pytest tests/unit/ -v
```

**Timeout:** 30s
**Expected:** All pass
**Reports:** Failures only

**Warning patterns:**
- `DeprecationWarning` - Report if from cite-assist code
- `PytestUnraisableExceptionWarning` - Report all

### Integration Tests

**Command:**
```bash
uv run pytest tests/integration/ -v -m integration
```

**Timeout:** 3 minutes
**Prerequisites:**
- FastAPI server running (localhost:8000)
- Qdrant running (localhost:6333)
- Embedding service running (localhost:8080)

**Expected:** All pass
**Reports:** Failures + connection errors

**Warning patterns:**
- Connection refused - Service not running
- Timeout - Service overloaded or stuck

### API v2 Tests

**Unit (schemas/transformers):**
```bash
uv run pytest tests/unit/api/v2/ -v
```

**Timeout:** 30s
**Expected:** All pass

**Integration (endpoints):**
```bash
uv run pytest tests/integration/api/ -v
```

**Timeout:** 3 minutes
**Prerequisites:** API server + Qdrant + embeddings

**Expected:** All pass
**Reports:** Failures + HTTP errors

**Warning patterns:**
- 4xx errors - Client error (report request/response)
- 5xx errors - Server error (report with stack trace)
- Slow responses (>5s) - Report timing

### Performance Tests

**Query performance:**
```bash
uv run pytest tests/integration/performance/query_performance_test.py -v
```

**Timeout:** 5 minutes
**Expected:** Pass with timing metrics

**Embedding load:**
```bash
uv run pytest tests/integration/performance/comprehensive_embedding_load_test.py -v
```

**Timeout:** 10 minutes
**Expected:** Pass with throughput metrics

**Reports:** Failures + performance degradation (>20% slower than baseline)

### Smoke Tests

**Command:**
```bash
uv run pytest tests/smoke/ -v
```

**Timeout:** 1 minute
**Expected:** All pass
**Reports:** Any failure (critical - indicates broken infrastructure)

**Warning patterns:**
- Service not reachable - Report immediately
- Database connection failed - Report immediately

### Large Batch Test (Production Scenario)

**File:** `tests/integration/api/test_v2_large_batch.py`

**Command:**
```bash
uv run python tests/integration/api/test_v2_large_batch.py
```

**Timeout:** 3 minutes
**Expected:**
- 200 status
- All queries return results
- Time: <30s (26 queries)

**Reports:** Failures + slow responses (>30s)

## Running All Tests

**Command:**
```bash
uv run pytest tests/ -v --ignore=tests/integration/performance/
```

**Timeout:** 5 minutes
**Expected:** All pass (excluding performance)

## Failure Interpretation

### Common Patterns

**`ConnectionError: [Errno 61] Connection refused`**
- **Cause:** Service not running
- **Fix:** Start service (see [embedding-service.md](embedding-service.md))
- **Report:** Service name + expected port

**`TimeoutError`**
- **Cause:** Service stuck or overloaded
- **Fix:** Restart service
- **Report:** Which service + timeout duration

**`AssertionError: expected 200, got 500`**
- **Cause:** Server error
- **Fix:** Check logs for stack trace
- **Report:** Endpoint + request params + error response

**`QdrantException: Collection not found`**
- **Cause:** Missing collection or wrong Qdrant instance
- **Fix:** Run sync scripts (see [qdrant-sync.md](qdrant-sync.md))
- **Report:** Collection name + available collections

**`KeyError` in test**
- **Cause:** API response schema mismatch
- **Fix:** Check API version compatibility
- **Report:** Expected vs actual schema

**`pytest.PytestUnraisableExceptionWarning`**
- **Cause:** Unclosed async resources
- **Fix:** Check test teardown
- **Report:** Resource type + test name

## Reporting Format

**For failures:**
```
❌ TEST FAILURE
Suite: [unit|integration|api|performance|smoke]
Test: test_name (file_path:line_number)
Error: <error type>
Message: <error message>
Context: <relevant params/state>
```

**For warnings:**
```
⚠️  WARNING
Type: [deprecation|connection|timeout|performance]
Test: test_name
Message: <warning message>
Impact: [low|medium|high]
```

**For success (brief):**
```
✅ All tests passed
Suites: [list]
Duration: Xs
```

## Service Dependencies

**Required for integration/API tests:**
1. **FastAPI server**: `uv run uvicorn core.api.main:app --port 8000`
2. **Qdrant**: `podman start qdrant` (or see [QUADLET_CONTAINER_MANAGEMENT.md](../QUADLET_CONTAINER_MANAGEMENT.md))
3. **Embedding service**: `podman start embedding-service` or start manually

**Check services:**
```bash
# API server
curl http://localhost:8000/health

# Qdrant
curl http://localhost:6333/collections

# Embeddings
curl http://localhost:8080/health
```

## Pre-commit Tests

Pre-commit hooks run:
- Ruff (linting)
- Ruff-format (formatting)
- Guide validation

See [pre-commit-hooks.md](pre-commit-hooks.md) for details.

## Agent Usage Pattern

**Task:** "Run integration tests and report failures"

**Agent workflow:**
1. Read this guide
2. Check service dependencies
3. Run tests with appropriate timeout
4. Parse output for failures/warnings
5. Report using reporting format above
6. Return to main agent with actionable summary

**Do NOT report:**
- Passing tests (unless specifically requested)
- Expected warnings from dependencies
- Verbose test output

**DO report:**
- Any test failures
- Warnings from cite-assist code
- Service connection issues
- Performance degradation
- Unexpected errors

## Troubleshooting

**Tests hang indefinitely:**
- Kill test process
- Check service logs
- Restart services
- Re-run with shorter timeout

**Random failures:**
- Check if services are warm
- Try running single failing test
- Check Qdrant data consistency
- See [troubleshooting.md](troubleshooting.md)

**All tests fail:**
- Verify services running
- Check Qdrant collections exist
- Verify test library (5673253) accessible
- Check environment variables

## Related Guides

- [pipeline-scripts.md](pipeline-scripts.md) - Running pipeline operations
- [embedding-service.md](embedding-service.md) - Embedding service management
- [qdrant-sync.md](qdrant-sync.md) - Collection management
- [troubleshooting.md](troubleshooting.md) - Pipeline debugging
- [pre-commit-hooks.md](pre-commit-hooks.md) - Pre-commit validation
