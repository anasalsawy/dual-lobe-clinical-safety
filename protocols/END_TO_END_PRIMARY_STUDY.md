# End-to-End Primary Study Runbook

This runbook evaluates the implemented Dual-Lobe clinical system on the frozen benchmark.

## Stage 1 — frozen execution

```bash
python -m dual_lobe_clinical.study_runner \
  --bundle frozen/study_v1 \
  --output-dir results/primary_v1 \
  --blinding-salt <secret-random-study-salt>
```

The command verifies frozen inputs, runs the Dual-Lobe system on each case, writes immutable raw results, and generates a blinded clinician review packet.

## Stage 2 — blinded adjudication

At least two clinician reviewers independently score every sample. Ties or disagreements require adjudication.

## Stage 3 — locked scoring

```bash
python -m dual_lobe_clinical.primary_score \
  --run-dir results/primary_v1 \
  --adjudications results/primary_v1/adjudications.jsonl
```

Scoring refuses to proceed if raw results changed or any sample lacks locked consensus.

## Integrity rule

No model output, benchmark case, adjudication, or primary result may be manually replaced after hashes are locked. Any correction requires a new study version.
