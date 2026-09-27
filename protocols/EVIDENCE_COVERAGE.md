# Evidence Corpus Coverage Matrix

The development corpus now covers 12 clinical safety domains with traceable
official U.S. sources. It remains intentionally unfrozen until external review.

## Covered domains

| Domain | Evidence ID |
|---|---|
| Warfarin + NSAID bleeding | DM_WARFARIN_NSAID_BLEED_2026 |
| NSAID + advanced renal impairment | DM_IBUPROFEN_RENAL_2026 |
| Metformin + severe renal impairment | DM_METFORMIN_EGFR_2026 |
| Serious beta-lactam allergy + amoxicillin | DM_AMOXICILLIN_BETALACTAM_ALLERGY_2026 |
| NSAID exposure during pregnancy | FDA_NSAID_PREGNANCY_20W_2020 |
| Aspirin-sensitive asthma + ibuprofen | DM_IBUPROFEN_ASPIRIN_ASTHMA_2026 |
| Sepsis warning features | CDC_SEPSIS_SIGNS_2026 |
| Severe hepatic disease + acetaminophen | DM_ACETAMINOPHEN_HEPATIC_2024 |
| QT/electrolyte risk + citalopram | DM_CITALOPRAM_QT_ELECTROLYTE_2026 |
| Older-adult hypoglycemia + glyburide | DM_GLYBURIDE_GERIATRIC_HYPOGLYCEMIA_2024 |
| Methotrexate + serious infection | DM_METHOTREXATE_SERIOUS_INFECTIONS_2026 |
| Acute stroke warning features | CDC_STROKE_SIGNS_2026 |

## Still required before primary freeze

Coverage should still be broadened enough to avoid a benchmark dominated by
medication-label cases. Candidate additions include:
- acute cardiovascular red flags;
- another unrelated high-risk drug-drug interaction;
- another hepatic dosing/contraindication example;
- lactation-specific risk;
- a clinically realistic evidence-conflict/adjudication example.

## Freeze rule

Do not set `status=primary_frozen` until:
1. all primary benchmark strata are fixed;
2. every positive case resolves to authoritative evidence IDs;
3. negative controls are independently reviewed;
4. at least two clinician reviewers have assessed case/gold-label validity;
5. disagreements are adjudicated;
6. corpus and benchmark hashes are locked before model runs.
