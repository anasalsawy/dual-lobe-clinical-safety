# Study Preregistration Draft

## Hypothesis

The implemented Dual-Lobe clinical supervisor will detect clinically important
context-dependent hazards while maintaining a measurable false-positive and
unnecessary-block rate.

## Primary metrics

- hazard recall/sensitivity
- precision
- specificity
- false-negative rate
- false-positive rate
- matched-pair discrimination

## Analysis discipline

- Freeze benchmark and gold labels before the primary run.
- Freeze prompts, gate thresholds, taxonomy, and guardian configuration.
- Do not drop failed cases from denominators.
- Report confidence intervals where appropriate.
- Report negative results and harms introduced by supervision.
- Separate exploratory analyses from preregistered primary analyses.
