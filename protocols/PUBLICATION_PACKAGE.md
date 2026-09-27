# Publication Package Layout

The repository is packaged around the editor's requested missing elements.

```text
dual-lobe-clinical-safety/
├── src/
│   ├── dual_lobe_crewai/          # inherited general dual-lobe runtime
│   └── dual_lobe_clinical/        # publication-specific clinical safety layer
│       ├── engine.py              # two-pass B runtime
│       ├── control_gate.py        # deterministic release logic
│       ├── evidence.py            # frozen evidence store + retrieval
│       ├── parsing.py             # structured B output parser
│       ├── prompts.py             # independent pass + final adversarial audit
│       ├── schemas.py             # findings, claim ledger, decisions
│       └── taxonomy.py            # frozen failure taxonomy
├── protocols/
│   ├── CONTROL_LOGIC.md
│   ├── DISAGREEMENT_POLICY.md
│   ├── FAILURE_TAXONOMY.md
│   ├── EVALUATION_PROTOCOL.md
│   ├── STUDY_PREREGISTRATION.md
│   └── REVIEWER_REQUIREMENTS_MATRIX.md
├── evidence/
│   └── evidence_manifest.json     # authoritative sources to be frozen before main study
├── benchmarks/
│   ├── clinical_case_schema.json
│   ├── clinical_cases_v1.jsonl    # currently development cases only
│   └── CLINICAL_BENCHMARK.md
├── evaluation/
│   ├── run_benchmark.py           # A0/A1/A2/A3 execution
│   └── metrics.py                 # initial automatic metrics
├── tests/
│   ├── test_logic.py
│   ├── test_clinical_control.py
│   └── test_clinical_two_pass.py
└── results/                       # generated raw outputs/metrics; no manual results
```

## Current status

IMPLEMENTED NOW:
- general Dual-Lobe parent runtime copied;
- clinical schemas and frozen taxonomy;
- deterministic safety gate;
- frozen evidence store and deterministic retrieval mechanism;
- explicit disagreement policy;
- two-pass clinical B architecture;
- B pre-answer independent safety pass;
- B final claim-by-claim adversarial audit;
- final B receives the observable A/child trace;
- trace SHA-256 fingerprinting;
- fail-closed handling of missing/ungrounded evidence;
- four study arms;
- benchmark runner;
- initial automatic metrics;
- development-only positive/negative latent-hazard pairs.

NOT YET COMPLETE:
- authoritative medical evidence corpus;
- full publication benchmark;
- clinician/expert adjudication;
- systematic related-work/reference package;
- full statistical analysis;
- final paper tables/results;
- exhaustive tests for every reviewer requirement.

Next stage is TEST HARDENING, then evidence/benchmark freeze, then primary experiments.
