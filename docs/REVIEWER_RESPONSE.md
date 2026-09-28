# Reviewer requirements: complete checklist

The review is split below into every distinct requirement it states or
implies, each quoted exactly. For each one: where it is met, the evidence,
and its status.

* **Done**: implemented and verified by tests or a reproducible artefact in
  this repository.
* **Ready to run**: the complete apparatus exists and is tested, but it needs
  the author's models or clinicians. No results are claimed for these.

The revised manuscript is [`paper/MANUSCRIPT.md`](../paper/MANUSCRIPT.md). The
formal reply is [`paper/RESPONSE_LETTER.md`](../paper/RESPONSE_LETTER.md).

## A. Strengths the reviewer identified (kept and strengthened)

| # | Reviewer | Realisation | Status |
|---|---|---|---|
| A1 | "identifies a legitimate clinical AI safety problem" | Problem stated formally as omission (METHODS §1; manuscript §1) | Done |
| A2 | "separation between generative execution and independent supervisory oversight" | A and B share no context before the audit; B is local, may be a different model, and cannot edit A's answer | Done |
| A3 | "a clinician may omit an important question, so a safety layer should examine patient context proactively rather than merely verify the literal answer requested" | B's context scan reads the whole record before seeing the answer (`prompts.B_CONTEXT_SCAN`). A same-model `answer_verifier` arm tests exactly "proactive context" vs "literal answer" | Done (design); ready to run (measurement) |
| A4 | "graphical architecture … independent oversight pathway connected to medical knowledge and patient context" | Architecture figure (README, mermaid; manuscript Fig. 1). B is connected to numbered patient facts and to deterministically retrieved knowledge `[K#]` | Done |

## B. "never develops that intuition into a sufficiently specified computational framework"

| # | Reviewer | Where met | Evidence | Status |
|---|---|---|---|---|
| B1 | "no formal control logic" | METHODS §2–3; manuscript §4 (grounding predicate, effective-verdict rules, 7-rule gate, execution order) | `control.py` is deterministic with no model calls; one test per rule (`test_clinical_control.py`); all 50,568 input configurations verified against 7 invariants (`test_gate_exhaustive.py`) | **Done** |
| B2 | "[no] evidence retrieval mechanism" | METHODS §5; manuscript §5 | Numbered record facts with stable paths; verbatim-quote verification; deterministic pre-call knowledge retrieval; only retrieved `[K#]` citable (`knowledge.py`, `control.ground_finding`, tests) | **Done** |
| B3 | "[no] disagreement policy" | METHODS §4; manuscript §4 | Six-point policy: no override by either lobe; evidence-gated interruption; findings shown first with their source; visible failure; independence before comparison; optional early resolution. Enforced by the gate and tested (B never alters A's answer; ungrounded objections cannot interrupt) | **Done** |
| B4 | "[no] failure taxonomy" | METHODS §6; manuscript §7 | 4 primary-lobe failure kinds × 3 severities, used as the machine-checked output schema (`models.py`); 12 system failure modes, each with its control and code location | **Done** |
| B5 | "[no] implementation" | `src/dual_lobe_clinical/` on `src/dual_lobe_crewai/`; CLI `dual-lobe-clinical` | 92 automated tests in CI; the provider boundary is exercised end to end | **Done** |
| B6 | "[no] comparison with existing verifier and supervisory approaches" | RELATED_WORK comparison table (9 approach families); manuscript Table 1 | Also an executable comparison: `answer_verifier` arm with the same model, record and schema | **Done** |

## C. "The lack of any references also prevents assessment of whether the proposed architecture contributes something distinct"

| # | Reviewer | Where met | Status |
|---|---|---|---|
| C1 | references | 42 references in the manuscript and RELATED_WORK, all cited in the text: verification, guardrails, multi-agent, AI control, clinical LLMs, CDS / alert fatigue / automation bias, de-identification, cryptography, statistics | **Done** (check formatting against the venue) |
| C2 | "contributes something distinct" | Four explicit distinctness claims (RELATED_WORK "What is claimed to be distinct"; manuscript §1), each tied to a test or measurement | **Done** (claims); ready to run (empirical support for claim 1) |

## D. "no empirical, simulated, analytical, or expert evidence showing …"

| # | Reviewer | Evidence type | Where | Status |
|---|---|---|---|---|
| D1 | "… that the supervisory lobe improves safety" | Analytical | METHODS §7 detection decomposition P(surfaced) = P(¬M) + P(M)·P(D\|M); gate invariants I1–I7 exhaustively verified | **Done** |
| | | Empirical | Paired 3-arm study (`run_study.py`), McNemar and Wilson statistics (`score.py`) | **Ready to run** |
| D2 | "… detects omitted contraindications reliably" | Empirical | 21 omission cases in 12 clinical domains with gold fact paths; sensitivity per arm and per case; **repeat consistency** across runs (reliability) | **Ready to run** |
| D3 | "… or avoids creating new false alarms" | Analytical | Every hold requires a grounded finding, so ungrounded output adds zero holds (I5), and every false hold points to a real, quoted record entry (METHODS §7) | **Done** |
| | | Empirical | 8 negative controls with distractors; false-hold rate per arm | **Ready to run** |
| D4 | "… and automation risks" | Design + tests | B never edits A (tested); source entry shown for every interruption; holds and UNVERIFIED need acknowledgement; a failed check can never pass (I2, proven); narrow GREEN; anti-sycophancy | **Done** (clinician-behaviour user study: future work, stated) |
| D5 | "expert evidence" | Expert | Blinded adjudication sheet with a separate key (`score.py --export-adjudication`); **κ, consensus, tie-break and adjudicated per-arm rates** (`adjudication.py`); gold-label validation step | **Ready to run** (needs clinicians) |
| D6 | "simulated evidence" | Integration | Scripted models at the provider boundary exercise every path (hold, advisory, fail-closed, blocked, fabricated evidence, remote B refused) | **Done** |

## E. "the present manuscript contains the motivating concept rather than the scientific development"

| # | Where met | Status |
|---|---|---|
| E1 | Revised manuscript `paper/MANUSCRIPT.md`: formal specification, related work, privacy, taxonomy, analytical properties, evaluation design, results so far, limitations, and a pending-results table to fill | **Done** (model results pending) |

## F. Beyond what was asked

| # | Addition | Why it matters |
|---|---|---|
| F1 | Identity-blind inference: random per-request tokens, AES-256-GCM vault, HMAC index with no plaintext copy, relative dates, 90+ ages, crypto-shredding after every request, privacy receipt | Answers the main trust barrier to clinical AI and makes a strong remote A usable |
| F2 | Local B enforced by destination, with no failover to A's provider | Makes the two-lobe split a privacy boundary |
| F3 | Local B as residual de-identifier | Catches uncued identifiers that neither rules nor a remote model can safely handle |
| F4 | Two-layer egress monitor that fails closed | Monitoring "all through the process", tested at the provider boundary |
| F5 | Leak probe in every study run | Privacy measured in the real experiment |
| F6 | Anchoring-free pre-answer scan run concurrently with A | Independence at no latency cost (METHODS §7) |
| F7 | Supervisor held to anti-deception: fabricated citations or quotes disqualify its objections | The overseer is itself audited |
| F8 | Deterministic privacy audit: 115 identifiers, 0 deterministic leaks, 97/97 clinical values preserved | Empirical privacy evidence already produced |

## G. What only the author can complete

1. Run the study with a local B and an A model:
   `python evaluation/run_study.py --repeats 3`, then
   `python evaluation/score.py …`. This completes D1, D2 and D3 empirically.
2. Have one or two clinicians validate the gold labels, then independently
   fill the blinded sheet and run `python evaluation/adjudication.py …`.
   This completes D5.
3. Paste the numbers into manuscript Table 4 and the abstract, as measured,
   including unfavourable ones.
4. Optionally, measure de-identification recall on the i2b2/UTHealth 2014
   corpus (requires a data-use agreement).
