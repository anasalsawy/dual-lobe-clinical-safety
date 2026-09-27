# End-to-End Primary Study Runbook

This runbook begins only after the clinician-gated freeze command has created a
`primary_frozen` bundle.

## Stage 1 — frozen execution

Run:

```bash
python -m dual_lobe_clinical.study_runner \
  --bundle frozen/study_v1 \
  --output-dir results/primary_v1 \
  --arms A0,A1,A2,A3 \
  --blinding-salt <secret-random-study-salt>
```

The command:
1. verifies every frozen-file SHA-256;
2. runs A0/A1/A2/A3 over exactly the frozen cases;
3. writes raw results and their manifest;
4. produces a blinded clinician review packet;
5. writes the arm/case key separately as `PRIVATE_blinding_key.json`.

Do not give the private key to reviewers.

## Stage 2 — blinded adjudication

At least two clinician reviewers independently score every sample using the
predefined review fields. Ties/disagreements require adjudication.

The study remains `awaiting_blinded_adjudication` until every sample has locked
consensus.

## Stage 3 — locked scoring

Run:

```bash
python -m dual_lobe_clinical.primary_score \
  --run-dir results/primary_v1 \
  --adjudications results/primary_v1/adjudications.jsonl
```

Scoring refuses to proceed if:
- raw results changed after review export;
- any sample lacks consensus;
- the blinding mapping is unavailable.

It emits `primary_results.json` with:
- sensitivity/recall, precision, specificity;
- false-positive/false-negative rates;
- matched-pair discrimination;
- 95% Wilson intervals;
- paired exact McNemar comparisons;
- input hashes.

## Two distinct endpoints

The study must report both:

**Candidate-answer endpoint**
- Was the model-generated clinical content itself correct/safe?

**System-safety endpoint**
- What did the deployed architecture actually release, revise, withhold, or
  escalate?

A blocked unsafe answer should count as a system interception even when its raw
candidate was poor. Conversely, excessive blocking is measured as unnecessary
block/alert burden. Do not collapse these endpoints into one score.

## Integrity rule

No model output, benchmark case, evidence record, adjudication, or primary
result may be manually replaced after the corresponding hashes are locked.
Any correction requires a new study version.
