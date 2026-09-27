# Dual-Lobe Clinical Safety

Research implementation derived from the general-purpose Dual-Lobe runtime.

## Research objective

Evaluate whether an independent supervisory inference pathway can detect
clinically important, context-dependent hazards that are omitted from the
explicit user question while controlling false alarms and unnecessary blocking.

## Core architecture

1. A receives the task and acts as the primary worker/delegator.
2. B begins an independent pre-answer safety/context pass before seeing A's final answer.
3. The runtime may supply B with additional supervisory information from context, tools, retrieval, or other configured sources.
4. A executes while observable tool/delegation/runtime events are recorded.
5. B later receives A's exact candidate answer plus the observable execution/provenance trace and performs a final adversarial clinical audit.
6. A deterministic gate resolves disagreement and decides PASS, WARN, REVISE, BLOCK, ESCALATE, or INSUFFICIENT_EVIDENCE.
7. Only PASS/WARN release the candidate in the clinical research runtime.

## Clinical safety functions

- context broadening and omitted-hazard detection;
- contraindication, interaction, allergy, renal/hepatic, pregnancy/lactation,
  age-specific, and urgent-red-flag checks;
- claim-by-claim final audit;
- disagreement handling;
- fail-closed malformed/ungrounded supervisor handling;
- privacy supervision;
- observable trace fingerprinting.

## Privacy

The clinical runtime sanitizes direct identifiers before inference, replaces
known identifiers with run-scoped opaque tokens backed by an AES-256-GCM local
vault, sanitizes observable traces, can locally rehydrate released text, and
destroys the run key on completion on a best-effort basis.

## Evaluation

The repository includes paired latent-hazard clinical cases, matched negative
controls, privacy cases, stress/failure-injection cases, clinician gold-label
review, blinded output adjudication, study freezing, result hashing, and
programmatic statistical scoring.

## Related work

The manuscript should cite representative verifier/supervisor approaches and
compare control flow, context visibility, persistence, and disagreement
handling. The repository does not define separate verifier-comparison
architectures as part of the core system.

## Scope

This is a research system, not a clinical decision-support product and not for
patient care. Claims must remain limited to measured study conditions.

## Parent runtime

The inherited general Dual-Lobe layer provides persistent A/B roles, live B
observation, anti-deception verification, delegation, consultation, memory,
provider controls, group identity/floor control, loop execution, and benchmark
scaffolding.
