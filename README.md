# Dual-Lobe Clinical Safety

Publication-grade clinical safety research implementation derived from the general-purpose `dual-lobe-proxy` architecture.

## Research objective

Evaluate whether an **independent supervisory inference pathway** can detect clinically important, context-dependent hazards that are omitted from the user's explicit question better than single-model generation or self-review, while controlling false alarms and unnecessary blocking.

## Experimental arms

- **A0 — Single model baseline**
- **A1 — Single model + self-review**
- **A2 — Independent Dual-Lobe supervisor**
- **A3 — Dual-Lobe supervisor + traceable medical evidence retrieval**

## Reviewer-driven requirements

This repository is designed to make the following elements explicit and reproducible:

1. formal control logic;
2. evidence retrieval;
3. disagreement policy;
4. predefined failure taxonomy;
5. working implementation;
6. comparison against verifier/supervisory baselines;
7. empirical/simulated evaluation;
8. false-alarm and automation-risk measurement;
9. reproducible methods, prompts, configurations, and results.

## Safety and scope

This is a **research system**, not a clinical decision-support product and not for patient care. Initial evaluation should use synthetic or de-identified clinical vignettes and frozen evidence sources. Claims about safety must remain limited to the measured benchmark conditions.

## Parent project

Derived from `anasalsawy/dual-lobe-proxy`. The parent architecture provides persistent A/B roles, live supervisory observation, anti-deception verification, memory, and benchmark scaffolding.


## Clinical runtime

The clinical research runtime now uses a **two-pass B**:

1. **Independent pass (concurrent with A):** B sees the original query, patient context, and frozen retrieved evidence, but not A's answer. It constructs safety obligations without answer anchoring.
2. **Final adversarial audit:** after A and delegated work finish, B receives A's exact answer, its prior independent assessment, the full observable execution/provenance trace, delegated results, and the same frozen evidence. B must construct a claim ledger for every material clinical claim.

A deterministic gate then decides whether the candidate may be released. The research runtime is fail-closed: only `PASS` and `WARN` release the candidate; `REVISE`, `BLOCK`, `ESCALATE`, and `INSUFFICIENT_EVIDENCE` withhold it.

The runtime records the count and SHA-256 fingerprint of the observable A/child trace supplied to final B. This does **not** claim access to a model's hidden chain-of-thought; it proves which observable tool/delegation/runtime events were available to B.
