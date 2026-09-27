# Novelty / Prior-Art Matrix

This matrix is intended to prevent overclaiming.

| Capability | Single LLM | Self-Refine | CoVe | Multi-agent debate | KALMV separate verifier | Medical guardrails | Clinical RAG | Dual-Lobe clinical hypothesis |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Separate generator and verifier | No | No | Not necessarily | Yes/multiple peers | Yes | Sometimes non-LLM | Not required | Yes |
| Verifier forms pre-answer independent patient-context view | No | No | Verification follows draft | Peers generate independently | Not its main target | No | No | Yes |
| Explicit omitted-context clinical hazard detection | No | No | Not primary target | Not primary target | Not primary target | Task-specific | Not inherent | Yes |
| Full observable execution/provenance audit | No | No | No | Not generally | Retrieval/generation focus | Sometimes task logs | Retrieval trace | Yes |
| Deterministic release gate independent of models | No | No | No | Usually consensus/aggregation | Error-triggered correction | Often yes | No | Yes |
| Frozen external medical evidence | No | No | Optional | Optional | Yes, external knowledge | Task-specific | Yes | A3 |
| Local-only known guardian model | No | No | No | Not inherent | Separate verifier possible | Not necessarily LLM | No | Yes |
| Patient identity vault / privacy egress supervision | No | No | No | No | No | Not central | Ethical issue, not inherent | Yes |
| Matched positive/negative latent-hazard evaluation | Not inherent | Not inherent | Not inherent | Not inherent | Not inherent | Task-specific | Not inherent | Yes |

## Interpretation

The closest conceptual precedent is KALMV because it explicitly trains a
separate verifier to detect errors in a knowledge-augmented generator.

Therefore the manuscript should describe the contribution as a clinically
specialized supervisory/control architecture and evaluation framework rather
than claiming invention of the general concept of a second verifier model.

The decisive evidence must come from the planned ablations:
- A1 vs A0: self-review benefit;
- A2 vs A1: benefit attributable to independent supervision;
- A3 vs A2: benefit attributable to external evidence retrieval.

If A2 does not outperform A1 on clinically important latent hazards at an
acceptable false-positive rate, the central architectural hypothesis is not
supported and the manuscript should report that result directly.
