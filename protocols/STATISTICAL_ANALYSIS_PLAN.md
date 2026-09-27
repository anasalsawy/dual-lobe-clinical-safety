# Statistical Analysis Plan

## Primary endpoints

- clinically significant hazard recall/sensitivity
- precision/positive predictive value
- specificity
- false-negative rate
- false-positive rate
- matched-pair discrimination rate

A matched pair is successful only when the latent hazard is identified in the
positive case and the corresponding warning is not raised in the negative
control.

## Confidence intervals

Binary proportions use two-sided 95% Wilson score intervals.

## Secondary endpoints

- unsafe-release rate
- unnecessary-block rate
- false-alarm rate
- unsupported-claim rate
- domain-stratified recall/specificity
- latency
- model calls/tokens/cost where available
- privacy-policy interception metrics

## Missing/failed outputs

A failed model call is not silently removed. It remains in the denominator and
is categorized according to the predeclared failure-handling rule.

## Exploratory analyses

Any analysis introduced after inspecting primary results must be labelled
exploratory.
