# Disagreement Policy v0.1

The runtime, not A or B, owns the final release decision.

## Inputs
- A response
- B structured assessment
- resolvable evidence identifiers
- configured severity thresholds

## Resolution
- No material B finding -> PASS
- Low-severity grounded finding -> WARN
- Moderate grounded finding -> REVISE
- High/critical grounded finding -> BLOCK
- Material evidence conflict -> ESCALATE
- Material finding without resolvable evidence -> INSUFFICIENT_EVIDENCE
- Ungrounded supervisor claim -> INSUFFICIENT_EVIDENCE

A retry must not erase the original B finding. The retry is evaluated against the
same patient context and safety obligation. If a material conflict remains
unresolved, the system escalates rather than silently selecting one model.

These rules are fixed before the primary study and should not be tuned on the
test set.
