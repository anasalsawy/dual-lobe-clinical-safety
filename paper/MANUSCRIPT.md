# Context-Conditioned Supervision for Clinical Language-Model Assistance: A Dual-Lobe Architecture with Evidence-Gated Release and Identity-Blind Inference

*Revised manuscript. Draft for the author's editing; results for the
model-performance study are marked as pending and must be filled in from
the actual run.*

## Abstract

**Background.** Clinicians often ask an AI assistant a narrow question
while the patient's record contains the fact that makes the requested
action unsafe. Verifiers, judges and guardrails for language models are
*answer-conditioned*: they check whether the output is good for the
question asked, and so they share the question's blind spot. Clinical use
also requires that patient identity is not disclosed to external model
providers.

**Objective.** To specify, implement and evaluate a supervisory
architecture that (i) proactively examines the whole patient context for
omitted hazards, (ii) controls false alarms and automation risk through a
deterministic, evidence-gated release policy, and (iii) keeps the answering
model blind to patient identity.

**Methods.** A primary lobe (A) answers the clinician's question from a
de-identified view of the record and may run on any provider. A supervisory
lobe (B) is required to run locally. It (1) sweeps outbound text for
residual identifiers, (2) scans the whole record for hazards concurrently
with A and without seeing A's answer, and (3) audits A's exact answer. Every
finding must cite numbered record facts with verbatim quotes, and citations
are verified deterministically. A seven-rule release gate lets only
grounded critical/major findings interrupt the clinician and fails closed
when supervision fails. A per-request privacy session replaces identifiers
with random tokens held in an AES-256-GCM vault, indexed only by keyed
hashes. It converts dates to relative offsets, monitors every outbound
payload by destination, and destroys its keys after each request. We
evaluate the design analytically (exhaustive verification of the gate),
deterministically (privacy audit), through integration tests at the provider
boundary, and with a paired three-arm study (A only; A plus a conventional
answer verifier; A plus the context-conditioned supervisor) on a 29-case
omission benchmark with negative controls and blinded clinician
adjudication.

**Results.** The release gate satisfies seven safety invariants on all
50,568 enumerated input configurations. These include that no ungrounded
objection can interrupt, that every grounded critical/major finding does,
and that a failed check can never be presented as passed. Across 29 cases
with 115 planted identifiers, the deterministic de-identification layer
removed 114, with no defects. The remaining one was an uncued place name,
the class the local residual sweep is designed to catch. All 97
non-identifying clinical values reached the answering model unchanged, and
every session's keys were destroyed. Model-performance results (omission
sensitivity, false-hold rate, repeat consistency) are **[pending: to be
reported from the study run]**.

**Conclusions.** The architecture turns the intuition that a safety layer
should look beyond the literal question into a specified, testable and
privacy-preserving system. Its claimed advantage over answer-conditioned
verification is isolated by a same-model comparison arm and is to be
established empirically.

## 1. Introduction

Diagnostic and treatment errors often arise not from a wrong answer to the
question asked, but from a question that should have been different:
premature closure on an initial frame [40]. When a clinician asks "what
ibuprofen dose?" for a patient whose record shows an eGFR of 28 while
taking an ACE inhibitor and a diuretic, the safety-critical fact is not in
the question. A language model that answers the dose question well has
still failed the patient.

Large language models encode substantial clinical knowledge [15][16][17]
but also hallucinate in the medical domain [20]. The dominant family of
safety mechanisms for them checks outputs. Examples are AI-feedback
critique [1], self-refinement [2][3], self-consistency [8], chain-of-verification [5], trained verifiers [9][10], LLM judges
[11], guardrail classifiers [12][13] and multi-agent debate [6][7]. These
mechanisms are conditioned on the answer or on the shared question. They
do not, by design, ask what the question failed to ask. Rule-based clinical
decision support (CDS) does scan the record proactively [21][26], but it is
limited to encoded rules and is known for alert fatigue and high override
rates [22][23].

A second barrier is trust in data handling. Sending identifiable patient
records to external model providers is often unacceptable, and memorisation
and extraction of training data by large models are documented [30].

This paper makes four contributions:

1. **Context-conditioned supervision.** A supervisory lobe reads the whole
   record, before and independently of the answer, to find omitted hazards.
   This avoids anchoring on the generator's framing [41].
   A same-model answer-verifier comparison arm isolates this design choice.
2. **A formal, deterministic control layer.** It comprises citation
   grounding, an effective-verdict rule and a seven-rule release gate. The
   gate implements an explicit disagreement policy (evidence-gated
   interruption, no override by either lobe) and is verified exhaustively.
3. **Privacy-asymmetric lobes.** The supervisor must be local. That keeps
   supervision on-premises and lets the supervisor act as the residual
   de-identifier for text about to leave. The answering model sees only a
   tokenised, date-shifted view, and every request ends with
   crypto-shredding of its keys.
4. **An evaluation apparatus.** It comprises an omission benchmark with
   negative controls and planted identifiers, paired arms, a leak probe
   in every run, and blinded clinician adjudication with inter-rater
   agreement.

## 2. Related work

Table 1 compares the approach with existing verifier and supervisory
methods. The full discussion and all 42 references are in
`docs/RELATED_WORK.md`.

**Table 1.** Supervisory approaches compared on the dimensions relevant to
omission.

| Approach | Conditioned on | Independent of generator's framing | Evidence required to object | Disagreement handling |
|---|---|---|---|---|
| Self-refinement / self-correction [2][3][4] | own answer | no | none | generator revises |
| Chain-of-Verification [5] | own claims | partly | none formal | generator revises |
| Trained verifiers / PRMs [9][10] | answer (steps) | yes | none (score) | rerank / reject |
| LLM-as-judge [11] | answer vs rubric | yes | none (score) | score |
| Guardrails [12][13] | policy categories | yes | none | block / allow |
| Multi-agent debate [6][7]; clinical multi-agent [18][19] | shared question | no / limited | informal | consensus or judge |
| AI-control trusted monitoring [14] | untrusted model's actions | yes | suspicion score | audit / replace |
| Rule-based CDS [21][22][26] | order + structured record | yes | encoded rule | interruptive / passive alert |
| **This work** | **whole record before the answer, then the exact answer** | **yes** | **cited facts, verbatim quotes, retrieved-knowledge IDs, machine-checked** | **evidence-gated interruption; clinician arbitrates** |

The closest structural analogue is trusted monitoring in AI control [14].
There, a trusted and possibly weaker model supervises an untrusted, more
capable one. We apply the same asymmetry to clinical omission and to data
protection. Unlike rule-based CDS, the supervisor can act on hazards carried
by free text (a positive home pregnancy test noted in passing). It is
expected to be less reliable than a curated rule base for well-encoded
interactions, so rule outputs can be supplied to it as retrieved knowledge.
Consistent with evidence that self-correction without external feedback is
unreliable [4], supervision here is performed by a separate lobe with no
shared context.

## 3. Architecture

**Figure 1.** Information flow.

```
clinician question + patient record ──► privacy session (in-process)
                                           │ de-identified view: numbered facts, tokens, relative dates
               ┌───────────────────────────┼─────────────────────────────┐
               ▼                           ▼                             ▼
     B0 residual sweep (LOCAL)   A: answer (any provider;      B1: context scan (LOCAL;
     before anything leaves      egress-monitored)             concurrent; never sees A's answer)
                                           │                             │
                                           └──────► B2: final audit ◄────┘  (LOCAL)
                                                         │
                                        deterministic grounding + release gate
                                                         │
                               rehydrate for the clinician only ─► destroy session keys
```

The record is flattened into numbered facts `F1…Fn` with stable paths.
Identifier fields are removed entirely, and a date of birth becomes an age.
A and B reference the same fact identifiers. B keeps the generic runtime's
adversarial persona, including explicit resistance to user-driven
sycophancy [42], and its anti-deception protocol. That protocol classifies
each claim as observed, inferred, assumed or unknown, requires positive
evidence, and fails closed. B never rewrites A's answer.

## 4. Formal control logic

**Grounding.** Let the sources be S = {Q: question, A: answer} ∪ {F1…Fn},
and let K be the knowledge snippet IDs retrieved in this request. A finding
is grounded iff:

1. every cited reference is in S ∪ K;
2. it cites what its kind requires: an unasked hazard or answer error cites
   at least one F; missing information cites an F or Q; an unsupported claim
   cites A;
3. its quote, if present, occurs (after normalisation) in a cited source.

Fabricated references or quotes make a finding ungrounded.

**Effective verdict.** GREEN is downgraded to YELLOW while any grounded
finding or open evidence gap exists. RED is downgraded to YELLOW unless a
grounded answer error or grounded critical finding supports it.

**Release gate.** The first matching rule wins (Table 2).

**Table 2.** Release rules.

| # | Condition | Release | Acknowledgement |
|---|---|---|---|
| 1 | outbound call refused by privacy monitor | BLOCKED | – |
| 2 | primary lobe produced no answer | UNVERIFIED | required |
| 3 | no supervision (baseline) | UNSUPERVISED | – |
| 4 | supervisor failed or unparsable | UNVERIFIED (fail closed) | required |
| 5 | grounded critical/major finding, or effective RED | HOLD_FOR_CLINICIAN | required |
| 6 | effective YELLOW or any other finding | RELEASE_WITH_ADVISORIES | – |
| 7 | otherwise | RELEASE | – |

**Disagreement policy.**
1. Neither lobe overrides the other, and the clinician arbitrates.
2. Interruption requires grounded evidence and critical/major severity.
   Other objections are passive advisories.
3. On a hold, findings are shown before the answer, each with its source
   record entry.
4. Supervisor failure is visible, never a silent pass.
5. B forms its view before seeing A's answer.
6. Optionally, live B challenges reach A during generation through a
   non-blocking channel, so A can resolve them itself.

## 5. Evidence retrieval

Patient evidence is the numbered fact list. Medical knowledge comes from an
institution-supplied corpus (formulary monographs, label excerpts, local
guidelines). Retrieval follows the retrieval-augmented pattern [37][38], but it is
done deterministically before B is called, using
the question and every fact as queries, and presented as `[K1…Kn]`. B may
cite only those IDs. Retrieval therefore does not depend on a local model's
tool-use ability, and the evidence B saw is fully known.

## 6. Identity-blind inference

A request-scoped privacy session:

1. registers structured identifiers (HIPAA Safe Harbor categories [31]) and
   drops them from the view;
2. propagates known identifiers, including capitalised name parts, into free
   text;
3. detects pattern- and cue-based identifiers (contact details, record
   numbers, titled or relation-cued names);
4. converts calendar dates to offsets from an index date and generalises
   ages over 89;
5. asks the **local** B to list residual identifiers in the text about to
   leave, accepting only strings that occur verbatim;
6. monitors every outbound payload by destination at two layers, the
   runtime prompt and every framework message including tool results, and
   refuses the call on failure;
7. rehydrates tokens locally, for the clinician's display only;
8. destroys its keys when the request ends.

The vault holds AES-256-GCM ciphertexts [32] and a keyed HMAC-SHA256 index
[33], with no plaintext copy of any identifier. Tokens are random per
request, and after key destruction nothing that outlived the request can be
resolved or linked. B is refused if its configured destination is not
local, and it has no failover to A's remote provider. Patient memory is
per-request and in-memory, and framework telemetry is disabled.

## 7. Failure taxonomy

B reports four kinds of primary-lobe failure: *unasked hazard*, *missing
information*, *answer error* and *unsupported claim*, each rated critical,
major or minor. Twelve system-level failure modes, each with a control, are
listed in `docs/METHODS.md` §6.2. They include supervisor miss, false
alarm, fabricated evidence, malformed output, verdict inflation, automation
bias, alert fatigue, identifier leakage, off-site supervisor, retention
after use, and correlated error between lobes.

## 8. Analytical properties

Let M be "A misses the hazard" and D "B raises a grounded interrupting
finding on it". Then P(surfaced) = P(¬M) + P(M)·P(D | M). Supervision adds
exactly P(M)·P(D | M), which vanishes only when B's misses coincide with
A's. Context conditioning, the pre-answer scan and a distinct local model
are the design's levers on P(D | M). The answer-verifier arm estimates the
difference they make.

Because a hold requires a grounded finding, every false hold is a
misjudgement of a real, quoted record entry. It is never a fabrication, and
the clinician can check it in seconds. A failed check is never presented as
passed.

Wall-clock time is T_sweep + max(T_A, T_scan) + T_audit, because the scan
runs concurrently with A.

## 9. Evaluation

**Benchmark.** 29 synthetic cases:

- 19 unasked hazards across drug–drug and drug–disease interactions,
  allergy, pregnancy and childbearing potential, renal dosing, paediatric [39], older-adult [36], device, boxed-warning, red-flag and critical-result
  domains;
- 2 missing-information cases;
- 8 negative controls, several with deliberate distractors.

Each case plants identifiers in structured fields and in narrative. Gold
labels were drafted from label-level facts and are validated by independent
clinicians before the run.

**Arms.** `a_only`, `answer_verifier` (same model, record and output schema
as B, but answer-conditioned) and `dual_lobe`. Models and retrieval are
held constant, with at least 3 repeats.

**Endpoints.** The primary endpoint is blinded clinician adjudication of
whether the gold issue was surfaced, whether there was a false alarm, and
whether the output would be harmful if followed. It uses two raters,
Cohen's κ, and a third rater for disagreements. Secondary endpoints are
automated screening sensitivity, false-hold rate, repeat consistency,
UNVERIFIED rate, planted-identifier leaks (a probe after the privacy
monitor in every run), latency and model calls. Statistics are Wilson
intervals [34] and the exact McNemar test [35] on outcomes paired by case
and repeat.

## 10. Results

### 10.1 Control logic

Exhaustive enumeration of the gate's input space was run over:

- supervision mode;
- privacy, primary-failure and supervisor-completion flags;
- seven verdict states;
- every set of up to two findings drawn from 24 (kind × severity ×
  grounded) types.

This gives 50,568 configurations. All satisfied seven invariants:

- I1: privacy dominates;
- I2: fail closed;
- I3: no hold without grounded evidence;
- I4: every grounded critical/major finding holds;
- I5: ungrounded findings never interrupt;
- I6: clean release implies no findings, no open gaps and GREEN;
- I7: no finding is dropped.

### 10.2 Privacy

**Table 3.** Deterministic privacy audit of the exact text the answering
model receives (29 cases).

| Measure | Value |
|---|---|
| Identifiers planted | 115 |
| Removed by deterministic layer | 114 |
| Leaks attributable to the deterministic layer | 0 |
| Left for the local residual sweep (uncued place name) | 1 |
| Non-identifying clinical values delivered unchanged | 97 / 97 |
| Sessions with keys destroyed | 29 / 29 |

Integration tests intercepting every payload at the provider boundary
confirm the following:

- no planted identifier reaches the remote lobe;
- the residual sweep and all B calls reach only the local model;
- a configuration with a remote B is refused before any payload leaves;
- malformed supervisor output yields UNVERIFIED;
- a fabricated quote cannot interrupt;
- A's answer is shown to the clinician unchanged.

### 10.3 Supervisory performance

**Table 4.** Omission detection and false alarms by arm. **[Pending: fill
from `evaluation/score.py` and `evaluation/adjudication.py`.]**

| Arm | Surfaced, hazard cases (95% CI) | Interrupted by B | False holds, negative controls (95% CI) | Repeat consistency | UNVERIFIED | Identifier leaks | Median latency |
|---|---|---|---|---|---|---|---|
| A only | – | n/a | n/a | – | n/a | – | – |
| A + answer verifier | – | – | – | – | – | – | – |
| A + context-conditioned supervisor | – | – | – | – | – | – | – |

Paired comparisons (exact McNemar): dual-lobe vs answer verifier, and
dual-lobe vs A only. **[Pending.]** Inter-rater agreement (κ):
**[Pending.]**

## 11. Discussion

The central claim is narrow and testable. A supervisor conditioned on the
whole record, and formed before it sees the answer, surfaces omitted
hazards that an answer-conditioned verifier with the same model and
information does not, without an unacceptable false-hold rate. The design
treats false alarms as a first-class harm, following the CDS alert-fatigue
literature [22][23]. It also treats automation bias as a design constraint
[24][25]: the supervisor never edits the answer, and it points the
clinician to the exact record entry behind every interruption.

The two-lobe split also carries the privacy argument. Only a local model
may read text that has not yet been cleared to leave. This makes the
supervisor the natural residual de-identifier, a role that neither rules
[27][28] nor a remote model can fill.

## 12. Limitations

- **Synthetic, author-written cases.** Gold labels need clinician
  validation. The benchmark is small, so only large between-arm differences
  are detectable, and a confirmatory study needs roughly 100 or more hazard
  cases, ideally drawn from real incidents.
- **Automated scoring is only a screen.** It uses term matching, so
  adjudication is primary.
- **In-sample privacy audit.** It is not an estimate of de-identification
  recall. That should be measured on a standard corpus [27].
- **Quasi-identifiers remain** in narrative [29].
- **Process memory.** Python cannot guarantee the erasure of transient
  string copies.
- **Clinician behaviour is untested.** The effect on clinician behaviour
  needs a user study.
- **Research use only.** This is not a medical device.

## 13. Conclusion

We specified, implemented and began evaluating a context-conditioned
supervisory architecture for clinical LLM assistance. It has a formally
defined, exhaustively verified release policy and identity-blind inference.
The implementation, benchmark and complete evaluation apparatus are
available, and the comparative model study is ready to run.

## Code and data availability

Code, benchmark, privacy audit results and evaluation scripts:
repository `anasalsawy/dual-lobe-clinical-safety`. The core runtime is
derived from `anasalsawy/dual-lobe-proxy`.

## References

1. Bai Y, et al. Constitutional AI: Harmlessness from AI Feedback. arXiv:2212.08073, 2022.
2. Madaan A, et al. Self-Refine: Iterative Refinement with Self-Feedback. NeurIPS 2023.
3. Shinn N, et al. Reflexion: Language Agents with Verbal Reinforcement Learning. NeurIPS 2023.
4. Huang J, et al. Large Language Models Cannot Self-Correct Reasoning Yet. ICLR 2024.
5. Dhuliawala S, et al. Chain-of-Verification Reduces Hallucination in Large Language Models. Findings of ACL 2024 (arXiv:2309.11495).
6. Du Y, Li S, Torralba A, Tenenbaum JB, Mordatch I. Improving Factuality and Reasoning in Language Models through Multiagent Debate. ICML 2024.
7. Irving G, Christiano P, Amodei D. AI Safety via Debate. arXiv:1805.00899, 2018.
8. Wang X, et al. Self-Consistency Improves Chain of Thought Reasoning in Language Models. ICLR 2023.
9. Cobbe K, et al. Training Verifiers to Solve Math Word Problems. arXiv:2110.14168, 2021.
10. Lightman H, et al. Let's Verify Step by Step. ICLR 2024.
11. Zheng L, et al. Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena. NeurIPS 2023 Datasets and Benchmarks.
12. Inan H, et al. Llama Guard: LLM-based Input-Output Safeguard for Human-AI Conversations. arXiv:2312.06674, 2023.
13. Rebedea T, et al. NeMo Guardrails: A Toolkit for Controllable and Safe LLM Applications with Programmable Rails. EMNLP 2023 (System Demonstrations).
14. Greenblatt R, Shlegeris B, Sachan K, Roger F. AI Control: Improving Safety Despite Intentional Subversion. ICML 2024 (arXiv:2312.06942).
15. Singhal K, et al. Large language models encode clinical knowledge. Nature 2023;620:172–180.
16. Singhal K, et al. Toward expert-level medical question answering with large language models. Nature Medicine 2025;31:943–950.
17. Nori H, et al. Capabilities of GPT-4 on Medical Challenge Problems. arXiv:2303.13375, 2023.
18. Tang X, et al. MedAgents: Large Language Models as Collaborators for Zero-shot Medical Reasoning. Findings of ACL 2024.
19. Kim Y, et al. MDAgents: An Adaptive Collaboration of LLMs for Medical Decision-Making. NeurIPS 2024.
20. Pal A, Umapathi LK, Sankarasubbu M. Med-HALT: Medical Domain Hallucination Test for Large Language Models. CoNLL 2023.
21. Bates DW, et al. Ten commandments for effective clinical decision support: making the practice of evidence-based medicine a reality. J Am Med Inform Assoc 2003;10(6):523–530.
22. van der Sijs H, Aarts J, Vulto A, Berg M. Overriding of drug safety alerts in computerized physician order entry. J Am Med Inform Assoc 2006;13(2):138–147.
23. Ancker JS, et al. Effects of workload, work complexity, and repeated alerts on alert fatigue in a clinical decision support system. BMC Med Inform Decis Mak 2017;17:36.
24. Goddard K, Roudsari A, Wyatt JC. Automation bias: a systematic review of frequency, effect mediators, and mitigators. J Am Med Inform Assoc 2012;19(1):121–127.
25. Parasuraman R, Riley V. Humans and automation: use, misuse, disuse, abuse. Human Factors 1997;39(2):230–253.
26. Sutton RT, et al. An overview of clinical decision support systems: benefits, risks, and strategies for success. npj Digit Med 2020;3:17.
27. Stubbs A, Kotfila C, Uzuner Ö. Automated systems for the de-identification of longitudinal clinical narratives: Overview of 2014 i2b2/UTHealth shared task Track 1. J Biomed Inform 2015;58(Suppl):S11–S19.
28. Neamatullah I, et al. Automated de-identification of free-text medical records. BMC Med Inform Decis Mak 2008;8:32.
29. Sweeney L. Simple Demographics Often Identify People Uniquely. Carnegie Mellon University, Data Privacy Working Paper 3, 2000.
30. Carlini N, et al. Extracting Training Data from Large Language Models. USENIX Security 2021.
31. U.S. Department of Health and Human Services. 45 CFR §164.514(b)(2) (Safe Harbor method); OCR Guidance Regarding Methods for De-identification of Protected Health Information, 2012.
32. Dworkin M. Recommendation for Block Cipher Modes of Operation: Galois/Counter Mode (GCM) and GMAC. NIST SP 800-38D, 2007.
33. Krawczyk H, Bellare M, Canetti R. HMAC: Keyed-Hashing for Message Authentication. RFC 2104, 1997.
34. Wilson EB. Probable inference, the law of succession, and statistical inference. J Am Stat Assoc 1927;22:209–212.
35. McNemar Q. Note on the sampling error of the difference between correlated proportions or percentages. Psychometrika 1947;12:153–157.
36. 2023 American Geriatrics Society Beers Criteria Update Expert Panel. American Geriatrics Society 2023 updated AGS Beers Criteria for potentially inappropriate medication use in older adults. J Am Geriatr Soc 2023;71(7):2052–2081.
37. Lewis P, et al. Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks. NeurIPS 2020.
38. Zakka C, et al. Almanac — Retrieval-Augmented Language Models for Clinical Medicine. NEJM AI 2024;1(2).
39. U.S. Food and Drug Administration. FDA Drug Safety Communication: FDA restricts use of prescription codeine pain and cough medicines and tramadol pain medicines in children. April 20, 2017.
40. Graber ML, Franklin N, Gordon R. Diagnostic error in internal medicine. Arch Intern Med 2005;165(13):1493–1499.
41. Tversky A, Kahneman D. Judgment under uncertainty: heuristics and biases. Science 1974;185(4157):1124–1131.
42. Sharma M, et al. Towards Understanding Sycophancy in Language Models. ICLR 2024.

