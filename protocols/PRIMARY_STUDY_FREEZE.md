# Primary Study Freeze Procedure

The primary benchmark is never created by manually renaming a development file.

Use the freeze command only after:
- clinician gold-label review is complete;
- all cases are approved;
- the local B guardian model/adapter is frozen and hash-verified.

The command writes:
- clinical_cases.primary.jsonl
- guardian_manifest.primary.json
- gold_review_consensus.json
- study_freeze_manifest.json

The freeze manifest records SHA-256 hashes for all frozen inputs and their source files. Any later correction requires a new freeze version.
