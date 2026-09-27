# Local Clinical Guardian B

## Deployment invariant

A is provider-agnostic. B is the trusted supervisory guardian and is local-only by default.

The clinical runtime uses the dedicated provider role `B_CLINICAL`.

`B_CLINICAL`:
- requires a loopback/local endpoint;
- rejects remote base URLs;
- does not participate in cross-role failover;
- cannot silently fall back to A's external provider.

Default local endpoint:

```
http://127.0.0.1:11434/v1
```

## Why local B

B receives high-trust supervisory context:
- minimized clinical context;
- the complete observable A/child execution trace;
- additional supervisory information supplied by the runtime when needed;
- privacy receipts;
- disagreement state;
- potential policy violations.

Keeping B local means the independent supervisor is not another external patient-data recipient.

## Fine-tuned guardian responsibilities

1. `clinical_context_broadening`
   - identify clinically relevant facts omitted from the explicit question;
   - resist anchoring on A's answer.

2. `adversarial_claim_audit`
   - inspect material A claims;
   - distinguish supported, contradicted, and unresolved claims.

3. `privacy_oversight`
   - detect unnecessary disclosure, retention, re-identification attempts, and unsupported privacy claims.

## Model identity and reproducibility

The primary study freezes `guardian/guardian_manifest.json`, including model identifier, base model, fine-tune profile/version, local artifact path, SHA-256, training-data version, and intended supervisory roles.
