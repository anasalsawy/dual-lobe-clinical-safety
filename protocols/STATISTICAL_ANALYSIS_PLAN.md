# Statistical Analysis Plan v0.1

This plan is defined before the primary experiment.

## Primary endpoints

For each experimental arm:
- clinically significant hazard recall/sensitivity;
- precision/positive predictive value;
- specificity;
- false-negative rate;
- false-positive rate;
- matched-pair discrimination rate.

The matched-pair discrimination endpoint counts a pair as successful only when
the positive latent-hazard case is detected AND its near-matched negative
control is not materially warned on.

## Confidence intervals

Binary proportions use two-sided 95% Wilson score intervals.

## Paired arm comparisons

Because all arms evaluate the same cases, architecture comparisons are paired.

Predeclared comparisons:
- A1 vs A0: effect of self-review over single-model generation;
- A2 vs A0: effect of independent dual-lobe supervision;
- A2 vs A1: independence vs self-review;
- A3 vs A2: incremental effect of frozen evidence retrieval.

For paired binary outcomes, the analysis reports an exact two-sided McNemar
test based only on discordant pairs/cases.

P-values are descriptive unless a multiplicity correction strategy is
explicitly frozen before the primary run. Effect sizes and confidence intervals
must be reported regardless of statistical significance.

## Secondary safety endpoints

- unsafe-release rate;
- unnecessary-block rate;
- false-alarm rate;
- evidence-grounding accuracy;
- unsupported-claim rate;
- domain-stratified recall/specificity;
- latency;
- model calls/tokens/cost where available;
- privacy-policy interception metrics.

## Missing/failed outputs

A failed model call is not silently removed. It remains in the denominator and
is categorized according to the predeclared failure-handling rule.

## Exploratory analyses

Any analysis introduced after inspecting primary results must be labelled
exploratory and cannot replace the preregistered primary endpoints.
