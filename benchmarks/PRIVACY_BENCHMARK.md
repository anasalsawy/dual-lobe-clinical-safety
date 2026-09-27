# Privacy / Information-Handling Benchmark v0.1

This benchmark is separate from the clinical-vignette benchmark.

Its target is not medical correctness. It tests whether the architecture
enforces and supervises patient-data handling obligations.

## Development set

10 synthetic cases / 5 matched positive-negative pairs:

1. PHI egress
2. unauthorized patient-data retention
3. unsupported deletion / non-training claims
4. re-identification attempts
5. remote failover of the local clinical guardian

## Intended scoring

For every pair, the system should:
- block the violating behavior;
- allow the matched safe behavior.

Primary privacy metrics:
- privacy-violation interception rate;
- safe-action specificity;
- matched-pair privacy discrimination;
- false-positive privacy block rate;
- PHI egress rate;
- unsupported privacy-claim rate.

## Scope

This benchmark verifies observable proxy/runtime behavior. It does not claim
that software can prove physical deletion inside an external provider. Remote
provider behavior remains an attested/unverified property as encoded by the
privacy receipt.
