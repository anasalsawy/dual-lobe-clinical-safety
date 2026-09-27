# Clinical Evaluation Protocol v0.1

## Primary research question

Does an independent supervisory inference pathway detect clinically important,
context-dependent hazards omitted from the explicit user question better than
single-model generation or self-review, without an unacceptable increase in
false alarms or unnecessary blocking?

## Experimental arms

- A0: single-model response
- A1: single-model response followed by self-review
- A2: independent dual-lobe supervisor
- A3: independent dual-lobe supervisor with frozen evidence retrieval

The same benchmark cases, model family where feasible, sampling settings, and
scoring definitions must be used across arms.

## Primary endpoints

1. clinically significant hazard recall;
2. clinically significant hazard precision;
3. false-negative rate;
4. false-positive rate.

## Secondary endpoints

- omitted-context detection rate;
- evidence-grounding accuracy;
- unsupported-claim rate;
- unnecessary-block rate;
- disagreement-resolution accuracy;
- latency;
- token use;
- monetary cost.

## Benchmark construction

Cases should contain synthetic or appropriately de-identified patient context.
A subset must contain latent hazards that are present in context but omitted
from the explicit question. Every positive case should have a matched or
near-matched negative control to measure over-warning.

Gold labels and endpoint definitions should be frozen before the main run.
Clinical expert review should be obtained before making strong clinical-safety
claims.

## Reproducibility

Every run should preserve:
- exact prompts and model identifiers;
- sampling/configuration settings;
- benchmark version;
- evidence corpus version;
- raw A and B outputs;
- gate decisions;
- cited evidence IDs;
- timing/token/cost metadata;
- scoring code and generated tables.

No manually transcribed aggregate result should be treated as the source of
truth when it can be generated from raw run artifacts.
