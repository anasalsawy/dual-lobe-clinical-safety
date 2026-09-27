# Reviewer Requirements Matrix

This document maps the editorial concerns to the implemented system and remaining validation work.

| ID | Editorial deficiency | Project answer |
|---|---|---|
| R1 | No sufficiently specified computational framework | Implemented A/B runtime, structured supervisory outputs, trace visibility, state transitions, and release logic. |
| R2 | No formal control logic | Deterministic model-independent SafetyGate with explicit PASS/WARN/REVISE/BLOCK/ESCALATE behavior. |
| R3 | No evidence/information retrieval mechanism | B receives original context and can receive additional runtime/tool/retrieved information through a generic supervisory-context path. No fixed medical corpus is required. |
| R4 | No disagreement policy | Explicit deterministic policy governs A/B disagreement, unresolved uncertainty, revision, blocking, and escalation. |
| R5 | No failure taxonomy | Predefined clinical, supervisory, automation, and privacy failure classes. |
| R6 | No implementation | Working executable runtime, CLI, tests, packaging, privacy membrane, local B routing, and study tooling. |
| R7 | No comparison with verifier/supervisory approaches | Concise related-work section situates Dual-Lobe against representative verifier/supervisor designs and explains control-flow differences. |
| R8 | No references / novelty cannot be assessed | Related-work references and architectural comparison included without a 'closest prior art' claim or oversized novelty apparatus. |
| R9 | No empirical/simulated/analytical/expert evidence | 48-case paired clinical benchmark, privacy benchmark, stress set, clinician-review workflow, and statistical analysis pipeline. |
| R10 | No evidence that B improves safety | Primary benchmark measures hazard detection, false negatives, false positives, unnecessary warnings/blocks, and matched-pair discrimination. |
| R11 | No evidence B detects omitted contraindications reliably | Benchmark contains latent hazards present in patient context but not foregrounded in the question. |
| R12 | No evidence B avoids new false alarms | Matched negative controls and specificity/false-positive metrics. |
| R13 | No evidence B avoids automation risks | Fail-closed runtime, explicit gate, failure injection, unsafe-release and unnecessary-block measurement. |
| R14 | Motivating concept rather than scientific development | Executable implementation plus reproducible benchmark/review/scoring pipeline. |
| R15 | Contribution not situated relative to existing work | Related-work section compares persistence, context visibility, control flow, and disagreement handling with representative verifier/supervisor systems. |
| R16 | Claims need supporting evidence | Raw outputs, blinded adjudication, generated metrics, hashes, and locked result artifacts. |

## Clinical B invariants

- B remains an independent supervisory/adversarial process.
- B forms a pre-answer safety view before seeing A's final answer.
- B sees the original patient/context data and query.
- B can receive additional information through runtime/tools when needed.
- B receives the observable A/child execution and provenance trace for final audit.
- B audits material clinical claims and omissions.
- Omitted hazards remain findings even if A's explicit statements are individually true.
- Deterministic runtime logic, not either model alone, owns release.

## Current package status

- Clinical benchmark: 48 cases / 24 matched pairs / 12 domains.
- Privacy benchmark: 10 cases / 5 matched pairs.
- Stress challenge set: 6 fail-closed/escalation cases.
- Gold-label clinician review workflow: implemented.
- Blinded output adjudication workflow: implemented.
- Pair-aware statistical analysis: implemented.
- Primary-study freeze tooling: implemented.
- Local B guardian manifest/routing: implemented; actual model artifact still must be supplied for a frozen primary run.

## Remaining external work

1. Clinician review/adjudication of the clinical benchmark.
2. Freeze the actual local B artifact/configuration used in the study.
3. Run the frozen benchmark.
4. Perform blinded clinician adjudication of outputs.
5. Generate locked statistical results.
6. Write Results, Error Analysis, Discussion, and Limitations from those artifacts.
