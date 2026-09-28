# Current checkpoint: Dual-Lobe Clinical Safety

Base: the generic Dual-Lobe runtime (`src/dual_lobe_crewai`), copied from
`anasalsawy/dual-lobe-proxy`. It has two additive hooks: provider specs and
egress filters in `run_one`, and context and B specs for `LiveBMonitor`.

Clinical layer (`src/dual_lobe_clinical`):
- privacy session: de-identified view, AES-GCM vault with HMAC index,
  relative dates, 90+ ages, rehydration for display only, key destruction per request;
- egress monitor at runtime and CrewAI layers, destination-based, fails closed;
- Lobe B must be local; no cross-role failover for B;
- local residual identifier sweep; concurrent pre-answer context scan; final audit;
- deterministic grounding and 7-rule release gate;
- baselines: answer_verifier, none.

Evidence: exhaustive gate verification; deterministic privacy audit;
provider-boundary integration tests; study harness ready (model results
pending; clinician validation pending).

The previous ChatGPT-built clinical attempt is in Git history before commit
"Reset to clean dual-lobe-proxy baseline".
