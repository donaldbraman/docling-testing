# Platform Regex Filter Analysis

**Generated:** 2025-10-16 19:56:43

**Source Directory:** `data/raw_pdf`

## Summary Statistics

- **Total PDFs Tested:** 207
- **Successful:** 205
- **Failed:** 2
- **Platform Covers:** 12 (5.9%)
- **Semantic Covers:** 193 (94.1%)

## Platform Distribution

- **ProQuest:** 11 (91.7%)
- **Annual_Review:** 1 (8.3%)

## Semantic Covers (No Platform Detected)

Found 193 semantic covers suitable for training:

- `bu_law_review_beyond_vawa.pdf`
- `bu_law_review_interest_convergence_working_class.pdf`
- `bu_law_review_internet_grows_up.pdf`
- `bu_law_review_law_and_culture.pdf`
- `bu_law_review_learning_from_history.pdf`
- `bu_law_review_nil_compliance.pdf`
- `bu_law_review_rediscovering_jacobson.pdf`
- `bu_law_review_standing_privacy_harms.pdf`
- `bu_law_review_suing_china_covid.pdf`
- `california_law_review_affirmative-asylum.pdf`
- `california_law_review_indeterminacy-separation.pdf`
- `california_law_review_judiciary-ada.pdf`
- `california_law_review_loving-borders.pdf`
- `california_law_review_morgan-democracy.pdf`
- `california_law_review_new-conservationism.pdf`
- `california_law_review_social-justice-conflicts.pdf`
- `california_law_review_voter-pay.pdf`
- `chicago_law_review_ai-business-judgment-rule-heightened-information-duty.pdf`
- `chicago_law_review_blueprint-protecting-us-companies-unfair-competition-fueled-forced-labor.pdf`
- `chicago_law_review_children-and-cars-watch-them.pdf`

... and 173 more

## Platform Covers (To Be Filtered Out)

Found 12 platform covers to filter:


### Annual_Review

- `gwu_law_review_the-ordinary-questions-doctrine.pdf` (confidence: 0.70)

### ProQuest

- `california_law_review_amazon-trademark.pdf` (confidence: 0.70)
- `california_law_review_incoherence-colorblind-constitution.pdf` (confidence: 0.70)
- `columbia_law_review_overbroad_protest_laws.pdf` (confidence: 0.70)
- `michigan_law_review_citizen_shareholders_the_state_as_a_fiduciary_in_international_investment_law.pdf` (confidence: 0.70)
- `michigan_law_review_good_cause_for_goodness_sake_a_new_approach_to_notice_and_comment_rulemaking.pdf` (confidence: 0.70)
- `michigan_law_review_law_enforcement_privilege.pdf` (confidence: 0.70)
- `michigan_law_review_spending_clause_standing.pdf` (confidence: 0.70)
- `michigan_law_review_tort_law_in_a_world_of_scarce_compensatory_resources.pdf` (confidence: 0.70)
- `penn_law_review_super_dicta.pdf` (confidence: 0.70)
- `usc_law_review_islands_of_algorithmic_integrity_imagining_a_democratic_digi.pdf` (confidence: 0.70)

... and 1 more

## Next Steps

1. **Manual validation:** Review random sample of 20-30 PDFs
2. **Refine patterns:** Adjust regex if false positives/negatives found
3. **Extract text blocks:** Use Docling on semantic covers to count training samples
4. **Assess sufficiency:** Determine if semantic covers provide enough training data
