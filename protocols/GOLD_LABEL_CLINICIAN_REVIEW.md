# Pre-Study Clinical Gold-Label Review

The benchmark creator must not be the sole authority on the clinical gold
labels used to evaluate the architecture.

Before the benchmark can be marked `primary_frozen`, each case should be
reviewed independently by at least two clinicians.

## Review questions

For every vignette:
1. Is the proposed material-hazard label clinically correct?
2. If this is a negative control, is it truly negative for the target hazard?
3. Is the proposed expected gate (PASS/REVISE/BLOCK/etc.) appropriate?
4. Do the cited evidence IDs actually support the gold obligation?
5. Is the wording clinically plausible and not artificially giving away the answer?

Any tied/disputed item requires adjudication.

A case is eligible for freeze only when all five dimensions are approved after
consensus/adjudication.

## Separation from model-answer adjudication

This happens **before** A0/A1/A2/A3 are run.

After model execution, a separate blinded process judges the outputs. Keeping
these stages separate reduces circularity:
- clinicians first validate what the case means;
- later reviewers judge what each model actually did.
