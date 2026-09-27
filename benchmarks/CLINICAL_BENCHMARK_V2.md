# Clinical Benchmark — Paired Latent-Hazard Design

## Purpose

Measure whether the implemented Dual-Lobe supervisor detects clinically important hazards that are present in patient context but omitted or deemphasized in the explicit question, while measuring false alarms on near-matched controls.

## Current development set

- 48 synthetic cases
- 24 positive/negative matched pairs
- 12 clinical domains
- easy/moderate/hard wording

## Pairing principle

Within a pair, the task/question remains the same or nearly the same. The safety-relevant patient fact is changed while irrelevant features are held as stable as practical.

## Gold annotations

Every positive case defines failure taxonomy IDs, expected gate behavior, and required safety concepts. Every negative control defines no material target hazard and expected PASS behavior.

## Before primary freeze

Obtain independent clinician review of case/gold-label validity, adjudicate disagreements, freeze case wording and labels, and preserve the frozen benchmark hash before model evaluation.
