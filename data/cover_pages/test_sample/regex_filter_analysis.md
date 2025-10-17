# Platform Regex Filter Analysis

**Generated:** 2025-10-16 19:45:21

**Source Directory:** `data/cover_pages/verified_covers/source_pdfs_cover_page_only`

## Summary Statistics

- **Total PDFs Tested:** 85
- **Successful:** 84
- **Failed:** 1
- **Platform Covers:** 83 (98.8%)
- **Semantic Covers:** 1 (1.2%)

## Platform Distribution

- **HeinOnline:** 68 (81.9%)
- **Annual_Review:** 10 (12.0%)
- **JSTOR:** 5 (6.0%)

## Semantic Covers (No Platform Detected)

Found 1 semantic covers suitable for training:

- `Hogan - Prosecutorial regimes and homicides in the United States was the differentiating shift at the COVID_cover_page.pdf`

## Platform Covers (To Be Filtered Out)

Found 83 platform covers to filter:


### Annual_Review

- `Garland - 2023 - The Current Crisis of American Criminal Justice A Structural Analysis_cover_page.pdf` (confidence: 1.00)
- `VT36J57X_Mitchell_Petersen_Progressive_Prosecutors_cover_page.pdf` (confidence: 0.70)
- `annurev-criminol-022422-121435_cover_page.pdf` (confidence: 1.00)
- `annurev-criminol-111523-122257_cover_page.pdf` (confidence: 1.00)
- `annurev-criminol-111523-122427_cover_page.pdf` (confidence: 1.00)
- `annurev-criminol-111523-122639_cover_page.pdf` (confidence: 1.00)
- `annurev-criminol-111523-122746_cover_page.pdf` (confidence: 1.00)
- `annurev-lawsocsci-061824-073536_cover_page.pdf` (confidence: 1.00)
- `annurev-lawsocsci-102612-133956_cover_page.pdf` (confidence: 1.00)
- `annurev-lawsocsci-110316-113310_cover_page.pdf` (confidence: 1.00)

### HeinOnline

- `2018 - The Paradox of Progressive Prosecution Notes_cover_page.pdf` (confidence: 1.00)
- `60BaylorLRev73_cover_page.pdf` (confidence: 1.00)
- `Akbar - 2018 - Toward a Radical Imagination of Law_cover_page.pdf` (confidence: 1.00)
- `Akbar - 2020 - An Abolitionist Horizon for _Police_ Reform_cover_page.pdf` (confidence: 1.00)
- `Alschuler - 1971 - Courtroom Misconduct by Prosecutors and Trial Judges_cover_page.pdf` (confidence: 1.00)
- `Barkow - 2004 - Administering Crime_cover_page.pdf` (confidence: 1.00)
- `Barkow - 2005 - Separation of Powers and the Criminal Law_cover_page.pdf` (confidence: 1.00)
- `Barkow - 2008 - Institutional Design and the Policing of Prosecutors Lessons from Administrative Law_cover_page.pdf` (confidence: 1.00)
- `Barkow - 2010 - Insulating Agencies Avoiding Capture through Institutional Design_cover_page.pdf` (confidence: 1.00)
- `Barkow - 2019 - Prisoners of Politics Breaking the Cycle of Mass Incarceration The 2019 Minnesota Law Review Sympos_cover_page.pdf` (confidence: 1.00)

... and 58 more

### JSTOR

- `Anderson et al. - 2019 - The Effects of Holistic Defense on Criminal Justice Outcomes_cover_page.pdf` (confidence: 1.00)
- `Crespo - 2018 - The hidden law of plea bargaining_cover_page.pdf` (confidence: 1.00)
- `Huq - 2019 - Racial equity in algorithmic criminal justice_cover_page.pdf` (confidence: 1.00)
- `Jackson - 1940 - The federal prosecutor_cover_page.pdf` (confidence: 1.00)
- `Rappaport - 2020 - Some doubts about democratizing criminal justice_cover_page.pdf` (confidence: 1.00)

## Next Steps

1. **Manual validation:** Review random sample of 20-30 PDFs
2. **Refine patterns:** Adjust regex if false positives/negatives found
3. **Extract text blocks:** Use Docling on semantic covers to count training samples
4. **Assess sufficiency:** Determine if semantic covers provide enough training data
