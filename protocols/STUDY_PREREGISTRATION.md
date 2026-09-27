# Study Preregistration Draft v0.1

## Hypothesis
Independent context-supervisory inference will improve detection of latent,
clinically significant hazards compared with a single model and self-review,
while its false-positive and unnecessary-block rates remain measurable and
bounded.

## Primary comparisons
A2 vs A0, A2 vs A1, and A3 vs A2.

## Primary metrics
Hazard recall, hazard precision, false-negative rate, false-positive rate.

## Analysis discipline
- Freeze benchmark and gold labels before the primary run.
- Freeze prompts, gate thresholds, taxonomy, and evidence corpus version.
- Do not drop failed cases from denominators.
- Report confidence intervals where appropriate.
- Report negative results and harms introduced by supervision.
- Separate exploratory analyses from preregistered primary analyses.
