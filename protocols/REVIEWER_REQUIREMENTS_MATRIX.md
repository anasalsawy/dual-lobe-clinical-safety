# Reviewer Requirements Matrix

This document turns the JBHI editorial review into an implementation and validation checklist.
The project is not considered publication-ready until every row has implementation evidence AND test evidence.

## Editorial strengths to preserve

1. Legitimate clinical AI safety problem.
2. Intuitive separation between generative execution and independent supervisory oversight.
3. Strong central idea: the clinician may omit the important question, so the safety layer must inspect patient context proactively rather than only verify the literal answer.
4. Independent oversight pathway connected to medical knowledge and patient context.
5. Clear architecture concept.

These are treated as design invariants, not items to replace.

## Deficiencies identified by the editor

| ID | Editorial deficiency | Required project answer | Current implementation artifact | Test/evidence required before paper |
|---|---|---|---|---|
| R1 | No sufficiently specified computational framework | Formalize inputs, A/B roles, state transitions, structured outputs, and release logic | `src/dual_lobe_clinical/engine.py`, `schemas.py`, `control_gate.py`, `protocols/CONTROL_LOGIC.md` | Unit tests for every state transition; end-to-end trace showing exact inputs/outputs |
| R2 | No formal control logic | Deterministic, model-independent gate | `SafetyGate` with PASS/WARN/REVISE/BLOCK/ESCALATE/INSUFFICIENT_EVIDENCE | Boundary tests, malformed-output tests, fail-closed tests, transition coverage |
| R3 | No evidence retrieval mechanism | Frozen, traceable, reproducible evidence corpus + deterministic retrieval | `evidence.py`, `evidence/evidence_manifest.json` | Populate authoritative corpus; retrieval precision/coverage tests; provenance validation |
| R4 | No disagreement policy | Explicit rules for A/B disagreement and unresolved evidence | `protocols/DISAGREEMENT_POLICY.md`, deterministic gate | Tests for A correct/B wrong, A wrong/B correct, both wrong, evidence conflict |
| R5 | No failure taxonomy | Predefined taxonomy before primary study | `taxonomy.py`, `protocols/FAILURE_TAXONOMY.md` | Coverage across all planned hazard classes; inter-rater labeling protocol |
| R6 | No implementation | Working runtime, not just architecture diagram | Parent runtime copied + `dual_lobe_clinical` runtime and CLI | CI, install test, smoke test, end-to-end run, reproducibility package |
| R7 | No comparison with verifier/supervisory approaches | Controlled baseline arms | A0 single model; A1 self-review; A2 independent dual-lobe; A3 dual-lobe + evidence | Identical cases/config where possible; predeclared pairwise comparisons |
| R8 | No references / novelty cannot be assessed | Formal related-work review covering verification, guardrails, multi-agent critique, clinical CDS, retrieval-grounded safety | Placeholder only; not yet completed | Literature review with references + explicit novelty table |
| R9 | No empirical, simulated, analytical, or expert evidence | Controlled clinical-vignette benchmark | Benchmark runner, metric scaffold, development cases | Main frozen benchmark; clinician/expert labeling if feasible; statistical analysis |
| R10 | No evidence that B improves safety | Measure detection benefit vs A0/A1 | A0-A3 experimental design | Hazard recall/precision, false-negative rate, pairwise effect sizes/confidence intervals |
| R11 | No evidence B detects omitted contraindications reliably | Latent-hazard cases where risk is in context but absent from query | Two-pass B; development latent-hazard cases | Dedicated contraindication/interaction/organ-function benchmark strata |
| R12 | No evidence B avoids new false alarms | Matched negative controls | Development positive/negative pairs; benchmark rules | False-positive rate, specificity, unnecessary-warning rate |
| R13 | No evidence B avoids automation risks | Fail-closed runtime + explicit release gate | Gate + `released_answer=None` for unresolved/revise/block/escalate | Unnecessary-block rate, unsafe-release rate, alert burden, failure injection |
| R14 | Manuscript is motivating concept rather than scientific development | Produce executable system + frozen protocol + benchmark + results | Repo packaging in progress | Full reproducible artifact, raw outputs, metrics, tables, limitations |
| R15 | Need to assess whether contribution is distinct from existing literature | Isolate architectural independence from extra compute/retrieval | A1 vs A2 vs A3 design | Related-work comparison + ablation showing independence vs self-review vs retrieval |
| R16 | Need supporting evidence for stated claims | Every material study claim tied to generated result artifact | Raw-result and metrics pipeline scaffold | No hand-entered results; generated tables linked to raw run IDs |

## Clinical B invariants

The publication version must preserve ALL of the following:

- B remains an independent adversary, not a polite reviewer.
- B forms a pre-answer safety view before being shown A's answer.
- B sees the original patient/context data and query.
- B receives the complete observable A/child execution and provenance trace for final audit.
- B audits every material clinical claim in A's final answer.
- Agreement between A and B is not treated as evidence.
- B may not invent patient facts, citations, or evidence IDs.
- B itself is auditable; unsupported B claims fail closed.
- Omitted hazards remain findings even if every sentence A wrote is technically true.
- The deterministic gate, not either LLM, owns release.

## Publication package completion criteria

The project reaches the TEST STAGE only when implementation artifacts for R1-R16 exist.
The project reaches the RESULTS STAGE only when:
1. all deterministic/unit tests pass;
2. the evidence corpus is frozen and versioned;
3. the benchmark and gold labels are frozen;
4. all four arms can run from one command;
5. raw outputs are immutable;
6. metrics are generated programmatically;
7. negative controls are included;
8. failure injection tests exist;
9. CI is green.

The project reaches the PAPER STAGE only after the primary benchmark is run once under the frozen protocol and the results are analyzed without changing the preregistered primary endpoints.


## Status snapshot after evidence/benchmark/literature packaging

Legend:
- **IMPLEMENTED** = code/protocol exists and is testable now.
- **DEV-COMPLETE** = development artifact exists but is intentionally not primary-frozen.
- **EXTERNAL-EVIDENCE REQUIRED** = cannot be satisfied by code alone.

| Requirement | Status | Remaining work |
|---|---|---|
| R1 Computational framework | IMPLEMENTED | End-to-end primary run evidence |
| R2 Formal control logic | IMPLEMENTED | Primary-run trace |
| R3 Evidence retrieval | DEV-COMPLETE | Finish coverage, clinician review, mark corpus primary_frozen |
| R4 Disagreement policy | IMPLEMENTED | Empirical disagreement cases |
| R5 Failure taxonomy | IMPLEMENTED | Clinician review of taxonomy coverage |
| R6 Working implementation | IMPLEMENTED | Deployment smoke test with frozen local guardian |
| R7 Baseline comparisons | IMPLEMENTED | Run A0/A1/A2/A3 |
| R8 References / novelty | DEV-COMPLETE | Complete reproducible literature search and final extraction table |
| R9 Empirical/expert evidence | EXTERNAL-EVIDENCE REQUIRED | Clinician adjudication + benchmark run |
| R10 Evidence B improves safety | EXTERNAL-EVIDENCE REQUIRED | Comparative results |
| R11 Omitted contraindication reliability | DEV-COMPLETE benchmark design | Expand/freeze cases + results |
| R12 False alarms | DEV-COMPLETE matched controls | Results |
| R13 Automation risk | IMPLEMENTED metrics/gates | Results |
| R14 Beyond motivating concept | IMPLEMENTED architecture | Results required for manuscript claim |
| R15 Distinct from prior art | DEV-COMPLETE novelty matrix | Complete literature search + A1/A2/A3 ablation |
| R16 Claims supported by evidence | IMPLEMENTED pipeline | Generate locked study artifacts/results |

Current development benchmark: 28 cases / 14 matched pairs / 7 authoritative-evidence-backed domains.

No row marked EXTERNAL-EVIDENCE REQUIRED should be represented as solved until the
human/model study work is actually completed.
