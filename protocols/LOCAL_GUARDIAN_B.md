# Local Clinical Guardian B

## Deployment invariant

In the clinical architecture, **A is provider-agnostic; B is not**.

A may use a remote or local model selected for the clinical task. B is the
trusted supervisory guardian and is local-only by default.

The clinical runtime uses a dedicated provider role: `B_CLINICAL`.

`B_CLINICAL`:
- requires a loopback/local endpoint;
- rejects remote base URLs;
- does not participate in cross-role failover;
- therefore cannot silently fall back to A's external provider.

Default local endpoint:

```
http://127.0.0.1:11434/v1
```

This can be changed to another loopback-compatible local server such as a local
OpenAI-compatible runtime.

## Why local B

B receives the highest-trust supervisory context:
- minimized clinical context;
- the complete observable A/child execution trace;
- evidence provenance;
- privacy receipts;
- disagreement state;
- potential policy violations.

Keeping B local means the independent verifier is not another external data
recipient. It also permits a deliberately fine-tuned guardian model whose
behavior is controlled and reproducible.

## Fine-tuned guardian responsibilities

The frozen B model should be trained/evaluated for four roles:

1. `clinical_context_broadening`
   - identify clinically relevant facts omitted from the explicit question;
   - resist anchoring on A's answer.

2. `adversarial_claim_audit`
   - inspect each material A claim;
   - distinguish supported, contradicted, and insufficient-evidence claims.

3. `privacy_oversight`
   - detect unnecessary disclosure, retention, re-identification attempts, and
     unsupported deletion/privacy claims.

4. `evidence_discipline`
   - never invent evidence IDs;
   - explicitly mark uncertainty;
   - reject agreement-with-A as verification.

## Model identity and reproducibility

The primary study must freeze `guardian/guardian_manifest.json`.

The manifest records:
- exact model identifier;
- base model;
- fine-tune profile/version;
- local model/adapter artifact path;
- SHA-256 of that artifact;
- training-data version;
- intended supervisory roles.

Primary-study execution should not proceed when the guardian artifact cannot be
cryptographically matched to the frozen manifest.

This makes the paper's B reproducible rather than an unspecified "second LLM."
