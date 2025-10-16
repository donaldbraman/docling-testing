# cite-assist Guides Inventory & Recommendations

**Generated:** 2025-10-16
**Source:** Analysis of cite-assist/docs for reusable best practices

---

## 📋 Summary

cite-assist has 100+ guides covering development, deployment, and operations. This document identifies which ones are directly applicable to docling-testing.

**Directly Copyable (Recommended):** 8 guides
**Adapted for Our Use:** 3 guides
**For Reference Only:** 10+ guides

---

## 🟢 TIER 1: Copy Directly (Highest Priority)

These guides are ready to use as-is for docling-testing:

### 1. ✅ Astral Suite Guide
- **File:** `ASTRAL_SUITE_GUIDE.md`
- **Status:** ✅ ALREADY COPIED
- **Relevance:** Core development workflow using uv, ruff, typer
- **Action:** Already in place at `docs/guides/ASTRAL_SUITE_GUIDE.md`

### 2. ✅ Pre-Commit Hooks Guide
- **File:** `guides/pre-commit-hooks.md`
- **Relevance:** We need pre-commit hooks for code quality
- **Sections:** Configuration, validation, installation
- **Action:** SHOULD COPY - Set up documentation validation for our guides
- **Our Implementation:**
  - Validate model metadata in label_map.json
  - Ensure version bumps match model releases
  - Verify corpus stats match training checkpoints

### 3. ✅ Code Versioning Strategy
- **File:** `guides/code-versioning.md`
- **Relevance:** We follow semantic versioning (currently v3.0.0)
- **Sections:** Version format, when to increment, file storage
- **Action:** SHOULD COPY - Standardize our versioning approach
- **Our Implementation:**
  - Store version in `/VERSION` or `pyproject.toml`
  - Bump for model releases (v3.0.0, v3.1.0, etc.)
  - Document in label_map.json

### 4. ✅ Testing Workflow
- **File:** `guides/testing-workflow.md`
- **Relevance:** We use pytest for unit/integration tests
- **Sections:** Test commands, expectations, failure reporting
- **Action:** SHOULD COPY - Formalize our test execution
- **Our Implementation:** `pytest -m "not slow"` for fast tests

### 5. ✅ API Versioning Guide
- **File:** `guides/api-versioning.md`
- **Relevance:** Not directly applicable, but useful reference
- **Status:** Reference only (we're not building APIs)

### 6. ✅ Model Upgrade Workflow
- **File:** `guides/model-upgrade-workflow.md`
- **Relevance:** DIRECTLY APPLICABLE - We upgrade DoclingBERT models
- **Sections:** Pre-upgrade checks, rollback procedures, validation
- **Action:** SHOULD COPY AND ADAPT
- **Our Implementation:**
  - Pre-flight: Run full validation on new model
  - Upgrade: Train new model, generate checkpoint
  - Validation: Compare metrics to previous version
  - Rollback: Revert to previous v2-rebalanced if F1 < threshold

### 7. ✅ Troubleshooting Guide
- **File:** `guides/troubleshooting.md`
- **Relevance:** Common issues with model training, data processing
- **Action:** Reference for structure; adapt to our domain

### 8. ✅ Changelog / Version History
- **File:** Not directly named, but ADRs and phase accomplishments document decisions
- **Relevance:** We should maintain similar ADR (Architecture Decision Record) logs
- **Action:** Create docling-testing ADR directory for model design decisions

---

## 🟡 TIER 2: Adapt for Our Context (Medium Priority)

These need customization but provide valuable structure:

### 1. Agent Integration Guides
- **Files:** `guides/agent-messaging-complete-guide.md`, `reference/agent_integration.md`
- **Relevance:** Medium - useful if we integrate with cite-assist for model deployment
- **Sections:** Agent-to-agent communication, Redis messaging
- **Action:** Reference only for now; implement if we deploy models to cite-assist

### 2. Embedding Service Guides
- **Files:**
  - `guides/embedding-service.md`
  - `MODERNBERT_EMBEDDING_SERVICE.md`
  - `EMBEDDING_BEST_PRACTICES.md`
- **Relevance:** High - ModernBERT is basis for our spatial model
- **Sections:** Service optimization, chunking strategies, performance analysis
- **Action:** Reference for model serving best practices

### 3. Pipeline Diagnostics
- **File:** `guides/pipeline-diagnostics.md`
- **Relevance:** Medium - useful for debugging training pipeline
- **Sections:** Logging, monitoring, error detection
- **Action:** Reference for building our training diagnostics

---

## 🔵 TIER 3: Reference & Context (Lower Priority)

These provide valuable context but less directly applicable:

### Relevant for Background Knowledge:
- `adr/001-service-oriented-architecture.md` - SOA decisions
- `adr/002-batch-processing-strategy.md` - Batch processing patterns
- `EMBEDDING_SERVICE_OPTIMIZATION.md` - Performance tuning
- `CHUNKING_COMPARISON_PHASE1_REPORT.md` - Chunking strategies
- `qdrant-sync.md` - Vector database operations (if we use Qdrant)

### Not Directly Applicable:
- Zotero-specific guides
- Pin-Citer integration docs
- Docker/Podman container guides (we don't use containers)
- Redis guides
- Service management docs

---

## 📦 Installation Checklist

Copy these immediately:

```bash
# From cite-assist to docling-testing/docs/guides/

# Already done:
✓ ASTRAL_SUITE_GUIDE.md

# Should do now:
☐ guides/pre-commit-hooks.md
☐ guides/code-versioning.md
☐ guides/testing-workflow.md
☐ guides/model-upgrade-workflow.md
☐ guides/troubleshooting.md
☐ guides/api-versioning.md (reference)

# Create for docling-testing:
☐ adr/ directory for Architecture Decision Records
☐ CHANGELOG.md for version history
```

---

## 🎯 Recommended Next Steps

### Immediate (This Session)
1. Copy pre-commit-hooks.md
2. Copy code-versioning.md
3. Copy testing-workflow.md
4. Create ADR directory for model decisions

### Soon (Next Sprint)
1. Copy model-upgrade-workflow.md (customize for our use)
2. Set up pre-commit hooks in docling-testing
3. Formalize version management (v3.0.0 → v3.1.0 workflow)

### Later (As Needed)
1. Implement agent messaging if integrating with cite-assist
2. Reference embedding service guides for model serving
3. Use pipeline diagnostics for training monitoring

---

## 🔄 Synchronization Strategy

As cite-assist updates these guides, we should:

1. **Periodically review** - Check for improvements quarterly
2. **Cherry-pick** - Copy specific sections if frameworks change
3. **Maintain differences** - Don't blindly sync; keep our domain-specific customizations
4. **Document derivations** - Note in each copied guide: "Adapted from cite-assist v2.x"

---

## 📚 Cross-Repo Learning

Key patterns from cite-assist we should adopt:

| Pattern | cite-assist | docling-testing |
|---------|---|---|
| **Package Manager** | uv | ✓ Already using |
| **Linter/Formatter** | ruff | ✓ Already using |
| **Semantic Versioning** | MAJOR.MINOR.PATCH | ✓ Currently v3.0.0 |
| **Pre-commit hooks** | Validates docs accuracy | ✓ Should implement |
| **Test framework** | pytest + uv run | ✓ Already using |
| **ADR/Decisions** | docs/adr/*.md | ✗ Should create |
| **Version storage** | /VERSION file | ✓ In pyproject.toml |
| **Changelog** | Phase accomplishments | ✗ Should create CHANGELOG.md |

---

## 📞 Reference Links

- cite-assist guides: `/Users/donaldbraman/Documents/GitHub/cite-assist/docs/guides/`
- cite-assist ADR: `/Users/donaldbraman/Documents/GitHub/cite-assist/docs/adr/`
- Global guides: `~/.claude/guides/`

---

**Recommendation:** Start with TIER 1 guides immediately. They're production-tested and directly applicable.
