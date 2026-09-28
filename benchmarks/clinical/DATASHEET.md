# Datasheet: Dual-Lobe Omission Benchmark v1.1

Structured after *Datasheets for Datasets* (Gebru et al., Commun. ACM 2021).

## Motivation

* **Purpose.** To measure whether a supervisory component surfaces
  patient-specific hazards that the clinician's question does not raise
  (omissions), without raising false alarms. It also measures whether
  patient identifiers leak to remote models.
* **Created by.** The manuscript author, as part of the Dual-Lobe clinical
  safety study. No external funding.

## Composition

| Type | n | Definition |
|---|---|---|
| `unasked_hazard` | 19 | The record contains a fact that makes the requested action unsafe or requires action; the question does not mention it |
| `missing_information` | 2 | A safe answer requires data that is absent from the record |
| `negative_control` | 21 | No patient-specific hazard: 8 independent controls (several with deliberate distractors) and 13 **matched twins** |
| **Total** | **42** | |

* **Matched twins** (`twin_of`) repeat a hazard case's question exactly and
  remove only the hazard fact (for example, eGFR 28 on an ACE inhibitor and
  a diuretic becomes eGFR 95 with no interacting drugs). Twins exist for 13
  of the 19 hazards. For the other 6, removing the hazard still leaves a
  genuine concern, so no clean control is possible. Examples: diphenhydramine
  remains inappropriate for any 84-year-old; a fluoroquinolone in a
  79-year-old keeps its tendon warning without steroids.
* **Clinical domains.** Drug–drug interaction; drug–disease; allergy;
  pregnancy and childbearing potential; renal dosing; paediatric; older
  adult; implanted device; boxed warning; red-flag diagnosis; unaddressed
  critical result; missing dosing data.
* **Fields.** `id`, `type`, `domain`, `question`, `record` (free-form JSON:
  structured fields and/or free-text notes), `gold.fact_paths` (record paths
  that establish the hazard), `gold.terms` (screening terms), `gold.summary`,
  `gold.basis` (authoritative source type), `phi` (every planted
  identifier), `phi_needs_residual_sweep` (identifiers without a structural
  cue), `twin_of`.
* **Record formats vary on purpose** (nested `patient` objects, flat fields,
  `demographics`, lists of strings or objects, free-text notes) so that the
  system is not tuned to one schema.

## Provenance and collection

* **Entirely synthetic.** Every person, identifier, address, phone number
  and email is fictitious. Emails use reserved `example.*` domains; phone
  numbers use the fictional 555 prefix. No real patient data was used or
  consulted.
* **Label source.** Each hazard's gold label is drafted from a widely
  established, label-level or guideline-level fact recorded in `gold.basis`
  (for example, the simvastatin prescribing information contraindicating
  strong CYP3A4 inhibitors). Cases were chosen for clinical consensus, not
  for difficulty or novelty.
* **Validation status.** Author-drafted. **Independent clinician validation
  is required before any result is reported** (docs/EVALUATION.md). Record
  the validators' specialties, whether each label was confirmed or
  corrected, and the date.
* **Versioning.** Every study output row records the SHA-256 of `cases.json`,
  the code commit and the models used (`run_study.provenance`). Freeze the
  file (tag or commit) before a confirmatory run.

## Intended and inappropriate uses

* **Intended:** comparative evaluation of supervisory or verification
  components for clinical LLM assistance, and privacy regression testing.
* **Not intended:** estimating real-world prevalence of hazards; certifying
  clinical safety; training models (the set is too small, and test-set
  contamination would invalidate it).

## Limitations

* The cases are short and clean compared with real records. Performance on
  real, noisy, long records is expected to be lower.
* 21 hazard cases can detect only large differences between arms; see the
  sample-size note in docs/EVALUATION.md.
* The same author wrote the benchmark and the system. Mitigations are
  clinician validation, clinician-contributed additional cases, and a
  frozen hash before the run.
* Screening terms (`gold.terms`) support only automated triage. Clinician
  adjudication is the primary endpoint.

## Maintenance

Issues and additions go through the repository. Add new cases with new IDs
and never edit a frozen version in place; bump `version` instead.
