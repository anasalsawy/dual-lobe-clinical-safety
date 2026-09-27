# Clinical Evaluation Protocol

## Primary research question

Does the implemented independent supervisory pathway perform its intended function: detect clinically important context-dependent hazards omitted from the explicit user question, while avoiding an unacceptable increase in false alarms or unnecessary blocking?

## Primary endpoints

- clinically significant hazard recall
- clinically significant hazard precision
- false-negative rate
- false-positive rate
- matched-pair discrimination

## Secondary endpoints

- omitted-context detection rate
- unsupported-claim rate
- unnecessary-block rate
- disagreement-resolution behavior
- latency
- token use
- monetary cost
- privacy-policy interception metrics

## Benchmark construction

Cases use synthetic or appropriately de-identified patient context. Positive cases contain latent hazards present in context but omitted or deemphasized in the explicit question. Each positive case has a matched or near-matched negative control to measure over-warning.

Gold labels and endpoint definitions are frozen before the main run. Clinical expert review is obtained before strong clinical-safety claims are made.

## Reproducibility

Every run preserves exact prompts and model identifiers, configuration settings, benchmark version, raw A and B outputs, gate decisions, observable execution and provenance trace, timing and cost metadata, scoring code, and generated tables.