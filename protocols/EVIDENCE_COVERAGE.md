# Evidence Corpus Coverage Matrix

The evidence corpus is deliberately frozen only after benchmark hazard coverage is
complete. A source being present does not by itself validate a benchmark case;
case-level gold labels must cite one or more evidence IDs and undergo clinical review.

## Current authoritative coverage

| Hazard domain | Failure taxonomy | Current evidence | Status |
|---|---|---|---|
| Anticoagulant + NSAID bleeding interaction | F03 | DM_WARFARIN_NSAID_BLEED_2026 | Covered for development |
| NSAID use with impaired/advanced renal function | F07 / F04 | DM_IBUPROFEN_RENAL_2026 | Covered for development |
| Metformin with severe renal impairment | F02 / F07 | DM_METFORMIN_EGFR_2026 | Covered for development |
| Serious beta-lactam allergy + amoxicillin | F02 / F05 | DM_AMOXICILLIN_BETALACTAM_ALLERGY_2026 | Covered for development |
| NSAID exposure in pregnancy | F06 | FDA_NSAID_PREGNANCY_20W_2020 | Covered for development |
| Aspirin-sensitive asthma + ibuprofen | F02 / F04 | DM_IBUPROFEN_ASPIRIN_ASTHMA_2026 | Covered for development |
| Sepsis warning features / urgent red flags | F09 | CDC_SEPSIS_SIGNS_2026 | Covered for development |

## Coverage still required before primary freeze

The primary corpus should add authoritative evidence for at least:

- hepatic impairment / hepatotoxicity-sensitive prescribing;
- age-specific medication risk;
- additional high-risk drug-drug interactions from unrelated drug classes;
- additional disease-drug contraindications;
- additional pregnancy/lactation examples beyond NSAIDs;
- cardiovascular contraindication/risk examples;
- electrolyte/QT-prolongation risk;
- diabetes/hypoglycemia risk;
- immunosuppression/infection risk;
- emergency neurologic/cardiopulmonary red flags;
- evidence-conflict cases in which two sources require adjudication.

## Freeze rule

The manifest must remain `development_validated` until:
1. every benchmark hazard stratum has source coverage;
2. each gold-positive case identifies its supporting evidence IDs;
3. negative controls have been reviewed for absence of the target hazard;
4. source metadata passes automated provenance validation;
5. a clinician/expert review process has been completed or explicitly documented;
6. the manifest is versioned and changed to `primary_frozen`;
7. its SHA-256 is recorded in the primary run manifest.

This prevents post-hoc evidence changes after benchmark outcomes are known.
