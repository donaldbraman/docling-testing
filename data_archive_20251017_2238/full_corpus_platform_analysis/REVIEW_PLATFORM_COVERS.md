# Platform Cover Detection - Manual Review

**Date:** 2025-10-16
**Corpus:** Full PDF corpus (`data/raw_pdf/`)
**Total PDFs:** 207
**Platform Covers Detected:** 12 (5.9%)

---

## Instructions

Please review the **12 PDFs listed below** to verify they have platform-added cover pages:

1. Open each PDF
2. Check if the first page has platform signatures (HeinOnline, ProQuest, Annual Review, JSTOR headers/metadata)
3. Mark as ✅ (correct detection) or ❌ (false positive)

---

## Detected Platform Covers

### ProQuest (11 PDFs) - Confidence: 0.70

1. `california_law_review_amazon-trademark.pdf`
2. `california_law_review_incoherence-colorblind-constitution.pdf`
3. `columbia_law_review_overbroad_protest_laws.pdf`
4. `michigan_law_review_citizen_shareholders_the_state_as_a_fiduciary_in_international_investment_law.pdf`
5. `michigan_law_review_good_cause_for_goodness_sake_a_new_approach_to_notice_and_comment_rulemaking.pdf`
6. `michigan_law_review_law_enforcement_privilege.pdf` ✅ (verified - has ProQuest repository header)
7. `michigan_law_review_spending_clause_standing.pdf`
8. `michigan_law_review_tort_law_in_a_world_of_scarce_compensatory_resources.pdf`
9. `penn_law_review_super_dicta.pdf`
10. `usc_law_review_islands_of_algorithmic_integrity_imagining_a_democratic_digi.pdf`
11. `wisconsin_law_review_the_first_amendment_and_national_security.pdf`

**Note:** All ProQuest detections have confidence 0.70, meaning only 1 pattern matched (not 2+). This suggests they may have minimal ProQuest branding. Verify each one.

### Annual Review (1 PDF) - Confidence: 0.70

1. `gwu_law_review_the-ordinary-questions-doctrine.pdf`

**Potential False Positive:** This appears to be a George Washington Law Review article that *mentions* "Annual Review of Administrative Law" in its text, NOT an Annual Reviews journal publication. The regex matched the phrase "Annual Review" but this is likely incorrect.

---

## Semantic Covers (193 PDFs) - 94.1%

The remaining 193 PDFs were classified as semantic covers (no platform signatures detected). These will be used directly for training data extraction.

---

## Review Results

After reviewing, please note:
- **Total Correct:** ___ / 12
- **False Positives:** ___ / 12
- **Accuracy:** ____%

### False Positives Identified

List any PDFs incorrectly identified as platform covers:

1.
2.
3.

### Pattern Refinements Needed

If false positives found, note which regex patterns need adjustment:

-
-

---

## Next Steps

1. If accuracy ≥90%: Regex filters are production-ready
2. If accuracy <90%: Refine regex patterns and re-test
3. Once validated: Integrate regex filters into corpus extraction pipeline

---

**Full Results:** See `regex_classification_results.csv` and `regex_filter_analysis.md` in this directory.
