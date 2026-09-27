# Safety Stress Challenge Set v0.1

This challenge set complements the paired clinical benchmark.

It targets failure modes in which a supervisor can become dangerous by acting
too confidently:

- incomplete patient facts;
- conflicting evidence;
- correlated A/B errors;
- hallucinated evidence;
- malformed supervisor output;
- unsupported privacy/deletion claims.

The expected response is often `INSUFFICIENT_EVIDENCE` or `ESCALATE`, not a
clinical recommendation.

These cases should be used for deterministic/failure-injection testing and
reported separately from the primary latent-hazard sensitivity analysis.
