# Documentation Guides Status

**Last Updated:** 2025-10-16
**Status:** 12 guides now available (including 4 new from cite-assist)

---

## 📚 Available Guides

### Development & Tools

✅ **ASTRAL_SUITE_GUIDE.md** (from cite-assist)
- uv package management
- ruff linting/formatting
- typer CLI framework
- CI/CD integration
- Container deployment
- **Status:** Ready to use

✅ **pre-commit-hooks.md** (from cite-assist)
- Git hooks configuration
- Documentation validation
- Code quality checks
- Setup instructions
- **Status:** Ready to implement

✅ **code-versioning.md** (from cite-assist)
- Semantic versioning strategy
- Version file management
- Documentation synchronization
- **Status:** Ready to adopt (we're at v3.0.0)

✅ **testing-workflow.md** (from cite-assist)
- Test execution patterns
- pytest configuration
- Test reporting
- **Status:** Ready to follow (we use pytest)

### Model Development

✅ **model-training.md** (project-specific)
- Training new models
- Hyperparameter tuning
- Class weight rebalancing
- Checkpoint management
- **Status:** Complete

✅ **model-evaluation.md** (project-specific)
- Checkpoint evaluation
- Confusion matrix generation
- Performance metrics
- Model comparison
- **Status:** Complete

### Data & Corpus

✅ **LAW_REVIEW_COLLECTION_STRATEGIES.md** (NEW - for sub-agents)
- Multi-stage discovery pipeline
- 5 parallel discovery strategies
- Tool selection per strategy
- Rate limiting & politeness
- Multi-agent coordination
- Troubleshooting & fallbacks
- **Status:** Ready for agent deployment

✅ **data-collection.md** (project-specific)
- PDF scraping approaches
- HTML/PDF pair collection
- Legal document sources
- **Status:** Complete

### Troubleshooting

✅ **troubleshooting.md** (project-specific)
- Common training issues
- Data processing problems
- Model evaluation troubleshooting
- **Status:** Complete

### Integration

✅ **cite-assist-integration.md** (project-specific)
- Model deployment to cite-assist
- API integration patterns
- Version compatibility
- **Status:** Complete

### Administrative

✅ **README.md** (guides index)
- Guide categories
- Quick reference
- When to read each guide
- **Status:** Current

✅ **CITE_ASSIST_GUIDES_INVENTORY.md** (NEW)
- Analysis of cite-assist guides
- Which guides to copy/adapt
- Tier-1, Tier-2, Tier-3 recommendations
- Synchronization strategy
- **Status:** Reference document

---

## 🎯 Key Reference: Which Guide to Read When

| Task | Guide |
|------|-------|
| **Getting started** | README.md |
| **Development setup** | ASTRAL_SUITE_GUIDE.md |
| **Training a model** | model-training.md |
| **Evaluating checkpoints** | model-evaluation.md |
| **Collecting corpus data** | LAW_REVIEW_COLLECTION_STRATEGIES.md |
| **Collecting PDFs/HTML** | data-collection.md |
| **Deploying to cite-assist** | cite-assist-integration.md |
| **Debugging issues** | troubleshooting.md |
| **Code quality** | pre-commit-hooks.md, code-versioning.md |
| **Running tests** | testing-workflow.md |

---

## ✅ Tools Status

All required tools are installed and verified:

```
System Tools:
✓ curl / wget
✓ git / pre-commit

Python (via uv):
✓ beautifulsoup4 (HTML parsing)
✓ requests (HTTP)
✓ feedparser (RSS feeds)
✓ lxml (XML/HTML)
✓ pandas (data handling)
✓ pypdf (PDF validation)
✓ typer (CLI)
✓ ruff (linting/formatting)
✓ pytest (testing)

Claude Code Tools:
✓ WebFetch (HTML retrieval)
✓ Bash (shell commands)
✓ Python (script execution)
✓ File Operations (Read, Write, Glob, Grep)
```

---

## 🚀 Recommended Next Actions

### Immediate (This Session)
- [ ] Review LAW_REVIEW_COLLECTION_STRATEGIES.md
- [ ] Prepare sub-agent deployment configuration
- [ ] Define agent mission/prompt templates

### Soon (Next Sprint)
- [ ] Set up pre-commit hooks
- [ ] Update CHANGELOG.md with v3.0.0 release notes
- [ ] Create ADR directory for model design decisions

### Later
- [ ] Implement agent messaging if integrating with cite-assist
- [ ] Copy model-upgrade-workflow.md from cite-assist
- [ ] Establish model serving best practices

---

## 📝 Guide Format Standard

All guides follow this structure:
- **Title & Metadata** (version, status)
- **Overview** (what and why)
- **Quick Reference** (commands/checklist)
- **Detailed Instructions** (step-by-step)
- **Troubleshooting** (common issues)
- **Resources** (links, references)

---

**To contribute a new guide:**
1. Create in `docs/guides/{topic}.md`
2. Follow format above
3. Add to this STATUS file
4. Update README.md
