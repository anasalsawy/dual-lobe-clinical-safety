# Response to the reviewer: requirement-by-requirement

Each item below is taken directly from the review. For each one: what was
asked, where it is met, and its status. **Done** means implemented and
verified by tests or by a reproducible artefact in this repository.
**Ready to run** means the complete apparatus exists but needs the author's
models or clinicians.

## What the reviewer valued (preserved and made concrete)

| # | Reviewer's point | How it is realised |
|---|---|---|
| V1 | "a clinician may omit an important question, so a safety layer should examine patient context proactively rather than merely verify the literal answer" | B's **context scan** reads the whole record *before* seeing A's answer and is explicitly mandated to find what was not asked (`prompts.B_CONTEXT_SCAN`). A same-model **answer-verifier arm** exists specifically to test whether this beats literal answer verification. |
| V2 | "separation between generative execution and independent supervisory oversight" | A (generator, possibly remote) and B (supervisor, local) share no context before the audit, may use different models, and B cannot edit A's answer. |
| V3 | "independent oversight pathway connected to medical knowledge and patient context" | B receives numbered patient facts and deterministically retrieved knowledge snippets, and must cite both. Citations are machine-checked (`docs/METHODS.md` §5). |

## What the reviewer said was missing

| # | Requirement (reviewer's words) | Where it is met | Status |
|---|---|---|---|
| R1 | "formal control logic" | `docs/METHODS.md` §2–3: information-flow table, execution order, grounding predicate, verdict rules, 7-rule release gate. Code: `control.py` (no model calls). Tests: `test_clinical_control.py` (one per rule) and `test_gate_exhaustive.py` (all 50,568 input configurations). | **Done** |
| R2 | "evidence retrieval mechanism" | Patient evidence: the record is flattened into numbered facts with stable paths; every finding must cite them with a verbatim quote. Medical knowledge: deterministic retrieval from an institutional corpus before the call; B may cite only retrieved `[K#]` IDs (`knowledge.py`, METHODS §5). | **Done** (a corpus is supplied by the deploying institution) |
| R3 | "disagreement policy" | METHODS §4: no override by either lobe; evidence-gated interruption; findings shown before the answer with the source record entry; failure is visible; independence before comparison; optional early resolution via live B. | **Done** |
| R4 | "failure taxonomy" | METHODS §6.1 (four primary-lobe failure kinds with severities, used as the output schema in `models.py`) and §6.2 (twelve system failure modes, each with its control and code location). | **Done** |
| R5 | "implementation" | `src/dual_lobe_clinical/` on the generic runtime in `src/dual_lobe_crewai/`; CLI `dual-lobe-clinical`; 90 automated tests in CI. | **Done** |
| R6 | "comparison with existing verifier and supervisory approaches" | `docs/RELATED_WORK.md`: comparison table over self-correction, CoVe, trained verifiers, LLM-as-judge, guardrails, debate, clinical multi-agent, AI-control trusted monitoring, rule-based CDS. Also an **executable** comparison: the `answer_verifier` arm. | **Done** |
| R7 | "lack of any references" | 42 references in `docs/RELATED_WORK.md`, covering verification, guardrails, multi-agent, clinical LLMs, CDS / alert fatigue / automation bias, de-identification, cryptography and statistics. | **Done** (verify formatting against the venue) |
| R8 | evidence that the supervisory lobe "improves safety" | Analytical: invariants I1–I7 proven exhaustively. Empirical: `evaluation/run_study.py` with paired arms, McNemar and Wilson statistics, and blinded clinician adjudication (`docs/EVALUATION.md`). | Analytical **done**; model study **ready to run** |
| R9 | "detects omitted contraindications reliably" | 21 omission cases in 12 clinical domains, with gold fact paths; sensitivity per arm; the `answer_verifier` comparison isolates context conditioning. | **Ready to run** (needs models, then clinician validation of labels) |
| R10 | "avoids creating new false alarms" | Design: only grounded critical/major findings can interrupt; ungrounded ones are proven never to interrupt (I5). Measurement: 8 negative controls with distractors; false-hold rate per arm. | Design **done and proven**; rate **ready to run** |
| R11 | "avoids … automation risks" | B never edits A (tested); every hold shows the source record entry; holds and `UNVERIFIED` require acknowledgement; a failed check never shows as passed (I2, tested); `GREEN` defined narrowly; anti-sycophancy in B's persona. METHODS §6.2. | **Done** (effect on clinician behaviour is future work: a user study) |
| R12 | "expert evidence" | Blinded clinician adjudication sheet plus a separate key (`score.py --export-adjudication`); gold-label validation step (`docs/EVALUATION.md`). | **Ready to run** (needs clinicians) |

## Beyond what was asked

| # | Addition | Why it strengthens the work |
|---|---|---|
| X1 | **Patient-identity privacy membrane**: random per-request tokens, AES-256-GCM vault, HMAC lookup with no plaintext index, relative dates, 90+ ages, key destruction after every request (crypto-shredding), privacy receipt. | Addresses the main adoption barrier for clinical AI (trust with patient data) and makes a remote A model usable. `docs/PRIVACY.md`. |
| X2 | **Local-B requirement, enforced by destination.** B cannot fail over to a remote provider; the proxy refuses to run otherwise. | Turns the two-lobe split into a privacy boundary, a second justification for the architecture. |
| X3 | **Local B as residual de-identifier.** B finds identifiers without structural cues before any text leaves. | Something neither rules nor a remote model can do safely; measured in the audit. |
| X4 | **Two-layer egress monitor** (runtime prompt and every CrewAI message, including tool results) that fails closed. | "Monitor all through the process", verified at the provider boundary in tests. |
| X5 | **Leak probe in every study run.** | Privacy is measured in the real experiment, not only assumed. |
| X6 | **Anchoring-free pre-answer scan run concurrently with A.** | Independence at no latency cost. |
| X7 | **Fabricated-evidence detection for the supervisor itself.** | The supervisor is held to the same anti-deception standard as the generator. |

## What the author still needs to do

1. Configure a local B (for example `ollama/llama3.1:8b`, or a medically
   tuned local model) and an A model, then run
   `evaluation/run_study.py --repeats 3`.
2. Have one or two clinicians validate the gold labels, then adjudicate the
   blinded sheet.
3. Report the results as measured, including false holds and `UNVERIFIED`
   rates, with the models named.
4. Optional, for the privacy claim: measure de-identification recall on the
   i2b2/UTHealth 2014 corpus (it requires a data-use agreement).
