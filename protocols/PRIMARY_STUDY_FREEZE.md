# Primary Study Freeze Procedure

The primary benchmark is never created by manually renaming a development file.

Use the freeze command only after:
- clinician gold-label review is complete;
- all cases are approved;
- evidence provenance validation passes;
- every positive case resolves to evidence IDs;
- the local B guardian model/adapter is frozen and hash-verified.

The command writes a new immutable study bundle containing:
- `clinical_cases.primary.jsonl`
- `evidence_manifest.primary.json`
- `guardian_manifest.primary.json`
- `gold_review_consensus.json`
- `study_freeze_manifest.json`

The freeze manifest records SHA-256 hashes for all frozen inputs and their source
development files.

The experiment runner should consume only this frozen package for the primary
study. If any source is changed afterward, a new freeze version is required.
