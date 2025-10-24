# Repository Cleanup: Markdown Archive Candidates

**Date:** October 21, 2025
**Purpose:** Identify old planning docs for archiving

---

## Files to KEEP

### Root Level
- ✅ `CLAUDE.md` - Project instructions
- ✅ `README.md` - Main repository readme

### docs/guides/ (All Keep - Active Documentation)
- ✅ `docs/guides/README.md`
- ✅ `docs/guides/TRAINING_QUICK_START.md` - Main training guide
- ✅ `docs/guides/model-training.md`
- ✅ `docs/guides/model-evaluation.md`
- ✅ `docs/guides/data-collection.md`
- ✅ `docs/guides/cite-assist-integration.md`
- ✅ `docs/guides/troubleshooting.md`
- ✅ `docs/guides/code-versioning.md`
- ✅ `docs/guides/pre-commit-hooks.md`
- ✅ `docs/guides/testing-workflow.md`
- ✅ `docs/guides/OCR_EVALUATION_GUIDE.md`

### docs/memory/ (All Keep - Active Analysis/PRDs)
- ✅ `docs/memory/alignment_methods_analysis.md` - **Just created**
- ✅ `docs/memory/sequence_alignment_classification_PRD.md`
- ✅ `docs/memory/overlay_pdf_generation_PRD.md`
- ✅ `docs/memory/classification_correction_experiments.md`

### Current Results (Keep - Recent Work)
- ✅ `results/ocr_pipeline_evaluation/BASELINE_EVALUATION_SUMMARY.md`
- ✅ `results/ocr_pipeline_evaluation/PHASE3_TEXT_MATCHING_SUMMARY.md`
- ✅ `results/sequence_alignment/REVIEW_INSTRUCTIONS.md`

---

## Files to ARCHIVE

### Category 1: Old Planning Docs (docs/ root)

**Superseded by guides/ or completed:**

1. `docs/BENCHMARK_PLAN.md` - Old planning doc
2. `docs/CONTINUATION_PROMPT.md` - Old session prompt
3. `docs/IMPLEMENTATION_PLAN.md` - Superseded by TRAINING_QUICK_START.md
4. `docs/RESEARCH_TEXT_CLASSIFICATION_METHODS.md` - Research notes
5. `docs/HTML_EXTRACTION_PATTERNS.md` - Implementation notes
6. `docs/multiclass-training.md` - Superseded by guides/model-training.md
7. `docs/training_guide.md` - Superseded by guides/TRAINING_QUICK_START.md
8. `docs/pdf_tag_quality_report.md` - One-time analysis

**Corpus building (completed work):**

9. `docs/CORPUS_DIVERSITY_ASSESSMENT.md`
10. `docs/CORPUS_CONSOLIDATION_REPORT.md`
11. `docs/CORPUS_CLEANUP_SUMMARY.md`
12. `docs/CORPUS_PLATFORM_COVER_CLEANING_REPORT.md`
13. `docs/PLATFORM_COVER_DETECTION_COMPLETE.md`
14. `docs/CURRENT_DATASET_ACTION_PLAN.md`
15. `docs/DATA_SIZING_QUICK_REFERENCE.md`
16. `docs/DATA_SIZING_RESEARCH_SUMMARY.md`
17. `docs/EMPIRICAL_DATA_SIZING_RESEARCH.md`
18. `docs/REPO_HYGIENE_ACTION_PLAN.md`

**Non-law collection (completed deployment):**

19. `docs/NON_LAW_COLLECTION_DEPLOYMENT_SUMMARY.md`
20. `docs/NON_LAW_REVIEW_COLLECTION_DEPLOYMENT_PLAN.md`
21. `docs/QUICK_START_NON_LAW_COLLECTION.md`

**Law review collection (completed):**

22. `docs/LAW_REVIEW_RECONNAISSANCE_REPORT.md`
23. `docs/COMPREHENSIVE_LAW_REVIEW_RECONNAISSANCE.md`
24. `docs/CITE_ASSIST_ISSUE_PLATFORM_COVERS.md`

### Category 2: Old Reports (docs/reports/)

**All reports are point-in-time analysis:**

25. `docs/reports/INITIAL_FINDINGS.md`
26. `docs/reports/BREAKTHROUGH_FINDINGS.md`
27. `docs/reports/SCALING_RESULTS.md`
28. `docs/reports/COMPARISON_FRESH_VS_SAVED.md`
29. `docs/reports/CORPUS_ANALYSIS.md`
30. `docs/reports/COLLECTION_REPORT.md`
31. `docs/reports/LAW_REVIEW_COLLECTION_SUMMARY.md`
32. `docs/reports/law_review_collection_report.md`
33. `docs/reports/georgetown_texas_collection_report.md`
34. `docs/reports/HARVARD_SCRAPING_REPORT.md`
35. `docs/reports/COLUMBIA_SCRAPING_REPORT.md`
36. `docs/reports/STANFORD_SCRAPING_REPORT.md`
37. `docs/reports/annual_reviews_download_list.md`
38. `docs/reports/annual_reviews_working_links.md`
39. `docs/reports/ocr_pipeline_comparison.md` - Superseded by results/ocr_pipeline_evaluation/

### Category 3: Old Agent Deployment Docs

**Completed agent deployments:**

40. `docs/agents/AGENT_1_PUBMED_CENTRAL.md`
41. `docs/agents/AGENT_2_ARXIV.md`
42. `scripts/deployment/agent_mission_template.md`

### Category 4: Old Guide Status/Inventory (Superseded)

**These were tracking guides before consolidation:**

43. `docs/guides/ASTRAL_SUITE_GUIDE.md` - External reference
44. `docs/guides/CITE_ASSIST_GUIDES_INVENTORY.md` - Inventory doc
45. `docs/guides/GUIDES_STATUS.md` - Status tracking
46. `docs/guides/EVALUATION_SESSION_STATUS.md` - Old session status
47. `docs/guides/LAW_REVIEW_COLLECTION_STRATEGIES.md` - Superseded by data-collection.md
48. `docs/guides/NON_LAW_REVIEW_COLLECTION_STRATEGY.md` - Superseded by data-collection.md

### Category 5: Old Issues Docs

**Completed issues:**

49. `docs/issues/ISSUE_CORPUS_V3_REBUILD.md`

### Category 6: Old Experiment Results

**Early experiments (superseded by OCR evaluation):**

50. `results/benchmark_test/report.md`
51. `results/docling/Green_Roiphe_2020.md`
52. `results/docling/Jackson_2014.md`
53. `results/docling/Nedrud_1964.md`
54. `results/experiment_2_reports/experiment_2_summary.md`
55. `results/experiment_2_reports/Green_Roiphe_2020_2x_scale_report.md`
56. `results/experiment_2_reports/Jackson_2014_2x_scale_report.md`
57. `results/experiment_2_reports/Nedrud_1964_2x_scale_report.md`
58. `results/scaling_test/Jackson_2014_scale_1.0x.md`
59. `results/scaling_test/Jackson_2014_scale_2.0x.md`
60. `results/scaling_test/Jackson_2014_scale_3.0x.md`

### Category 7: V3 Data Investigation Docs

**Point-in-time analysis during corpus building:**

61. `data/v3_data/README.md` - Keep or archive?
62. `data/v3_data/STATUS_REPORT.md`
63. `data/v3_data/CSV_ANALYSIS_FINDINGS.md`
64. `data/v3_data/AUTONOMOUS_WORK_SUMMARY.md`
65. `data/v3_data/version_comparison.md`
66. `data/v3_data/bu_law_review_online_building_new_constitutional_jerusalem_comparison_table.md`
67. `data/v3_data/california_law_review_affirmative-asylum_comparison_table.md`
68. `data/v3_data/investigation_notes/CRITICAL_FINDING_FUZZY_MATCHING_FALSE_POSITIVES.md`
69. `data/v3_data/article_reports/_TEMPLATE.md`
70. `data/v3_data/article_reports/california_law_review_amazon-trademark.md`

---

## Archive Structure Recommendation

Create archive directory:
```
docs_archive_YYYYMMDD/
├── planning/           # Category 1 (docs/ root planning)
├── reports/            # Category 2 (docs/reports/)
├── agents/             # Category 3 (agent deployment)
├── guides_deprecated/  # Category 4 (old guide status)
├── issues/             # Category 5 (completed issues)
├── experiments/        # Category 6 (old experiment results)
└── v3_investigation/   # Category 7 (v3 data investigation)
```

---

## Summary

**Total files to archive:** ~70 markdown files
**Keep:** ~20+ markdown files (CLAUDE.md, guides/, memory/, current results)

**Rationale:**
- Planning docs are completed/superseded
- Reports are point-in-time snapshots
- Guides have been consolidated into docs/guides/
- Experiments superseded by current OCR evaluation framework
- Agent deployment docs are one-time use
