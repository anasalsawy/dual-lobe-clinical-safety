# Prior-Art Extraction Table

This table is a structured seed for the formal literature review. It is designed
to answer the editor's specific concern that the manuscript did not establish
distinction from verification, guardrails, multi-agent critique, and clinical
decision support.

| Work | Separate verifier? | Pre-answer independent safety view? | External evidence? | Clinical? | Runtime/provenance audit? | Deterministic release gate? | Privacy guardian? | Relevance |
|---|---|---|---|---|---|---|---|---|
| Self-Refine (2023) | No | No | No | No | No | No | No | Same-model self-review baseline |
| Chain-of-Verification (2023) | Procedural verification | No; follows draft | Optional/no | No | No | No | No | Strong anti-anchoring verification precedent |
| Multi-agent Debate (2023) | Multiple peers | Yes | No | No | No | No | No | Independent model instances, but symmetric debate |
| KALMV (2023) | **Yes** | No | Yes | No | Retrieval/generation verification | Correction trigger, not clinical gate | No | **Closest general prior art** |
| Verify-and-Edit (2023) | Not persistent verifier | No | Yes | No | No | No | No | Evidence-grounded post-editing |
| Constitutional AI (2022) | Training-time AI feedback | No | No | No | No | No | No | Principle-driven supervision |
| Medical guardrails (2025) | Guardrails | No | Structured/task knowledge | Yes | Task-specific | Partly | No | Shows deterministic checks remain important |
| Biomedical RAG review/meta-analysis (2025) | No | No | **Yes** | Yes | No | No | No | Retrieval is a separate causal factor |
| Clinical adversarial hallucination study (2025) | No | No | No | **Yes** | No | No | No | Physician-validated synthetic safety benchmark precedent |
| Kenya clinical CDSS safety study (2026) | No | No | Guideline alignment assessed | **Yes** | Retrospective records | No | No | Measures both mitigated risk and new harmful recommendations |

## Defensible novelty statement

The project should **not** claim novelty for:
- a second model;
- a verifier;
- self-critique;
- multi-agent interaction;
- RAG;
- medical guardrails.

The testable contribution is the **combination** of:

1. an arbitrary provider-facing generator A;
2. a known local-only guardian B;
3. B constructing a patient-context safety representation before seeing A's answer;
4. final B access to the complete observable A/child execution trace;
5. claim-by-claim and omission-focused clinical auditing;
6. frozen evidence retrieval as a separately ablated component;
7. deterministic release control outside either model;
8. patient-identity minimization/encrypted token vault and privacy oversight;
9. matched positive/negative latent-hazard evaluation with blinded clinician adjudication.

The manuscript should phrase this as an architectural hypothesis and evaluation
framework until A0/A1/A2/A3 results establish whether it improves safety.

## Closest prior art

KALMV is the closest general architectural precedent because it trains a
separate smaller verifier to detect retrieval and generation errors. The
manuscript should cite it prominently and state the difference narrowly:
clinical context omission, pre-answer safety modeling, observable execution
audit, deterministic clinical release control, local guardian deployment, and
privacy stewardship.

Chain-of-Verification is also important because it explicitly tries to keep
verification answers independent of the draft. That supports—not weakens—the
reason for measuring pre-answer independence as a distinct design choice.

Clinical safety literature further makes clear why both sides of the tradeoff
must be measured: real-world and simulated studies show LLMs can both mitigate
risk and introduce harmful recommendations. The benchmark therefore includes
matched safe controls and unnecessary-block/false-alarm outcomes.
