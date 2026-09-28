# Related work and positioning

The reviewer asked whether the architecture adds anything distinct to the
large literature on AI verification, guardrails, multi-agent critique and
clinical decision support. This document compares it along the dimensions
that matter for the omission problem, and states where it overlaps and where
it differs.

## Comparison

| Approach | Who checks | Conditioned on | Independent of the generator's framing? | Evidence required for an objection | Disagreement handling | Privacy position |
|---|---|---|---|---|---|---|
| Self-refinement / self-correction [2][3][4] | the generator itself | its own answer | no | none | generator revises | same as generator |
| Chain-of-Verification [5] | the generator, via verification questions | its own answer's claims | partly (claims are re-queried) | none formal | generator revises | same |
| Trained verifiers / process reward models [9][10] | separate scorer | the answer (and steps) | yes | none (a score) | rerank or reject | same |
| LLM-as-a-judge [11] | separate model | the answer vs a rubric | yes | none (a score/preference) | score | same |
| Guardrail classifiers / programmable rails [12][13] | classifier or rules | input/output policy categories | yes | none | block or allow | typically same provider |
| Multi-agent debate [6][7] | peer models | the same question | no (shared question and transcript) | informal | converge, or a judge decides | same |
| Clinical multi-agent collaboration [18][19] | role-played specialist agents | the same question | limited | informal | consensus / synthesis | same |
| AI Control, trusted monitoring [14] | a weaker, trusted model | the untrusted model's actions | yes | suspicion score | audit or replace | trusted monitor is local by design |
| Rule-based CDS alerts (drug-interaction, allergy checkers) [21][22][26] | deterministic rules | the **order plus structured record** | yes | the encoded rule | interruptive or passive alert | local |
| **This work** | **local supervisory lobe + deterministic gate** | **the whole patient record, before seeing the answer**; then the exact answer | **yes (pre-answer scan, no shared context)** | **cited record facts, verbatim quotes, retrieved-knowledge IDs, all checked deterministically** | **evidence-gated interruption; no override by either side; clinician arbitrates** | **supervisor is local and also the residual de-identifier; generator sees de-identified data only** |

## What is borrowed

* **Separate verifier over self-correction.** Self-correction without
  external feedback is unreliable [4], which motivates an independent lobe
  over self-critique. The anti-deception claim ledger (OBSERVED / INFERRED /
  ASSUMED / UNKNOWN) is in the spirit of CoVe-style claim checking [5] and
  of calibrated judging [11].
* **Trusted monitoring of an untrusted model** [14]. A local, controlled
  model supervises a more capable external one. The same asymmetry appears
  here, applied to clinical omission and privacy rather than to deliberate
  subversion.
* **Proactive record scanning** is what interaction and allergy checkers in
  CPOE systems already do [21][26]. Their known failure is alert fatigue and
  high override rates [22][23]. The gate's evidence-gated, severity-gated
  interruption is a direct response to that literature, following Bates et
  al.'s guidance on fitting CDS into the workflow and minimizing
  interruption [21].
* **Retrieval of external knowledge** follows retrieval-augmented generation
  [37] and its clinical variants [38]. Retrieval here is deterministic and
  done before the call, and citations are verified.
* **Automation-bias mitigations** [24][25]: the supervisor never edits the
  answer, it shows the source record entry for every interrupting finding,
  and it defines `GREEN` narrowly.
* **Anti-sycophancy.** B's persona explicitly removes affective pressure
  from the user [42], which matters when a clinician strongly expects a yes.

## What is claimed to be distinct

These are claims to be tested, not assumed:

1. **Context-conditioned supervision aimed at omission.** Verifiers, judges
   and guardrails are *answer-conditioned*: they evaluate whether the output
   is good for the question asked. Debate and clinical multi-agent systems
   share the question's framing. The omission failure is that the question
   itself leaves out the hazard (premature closure [40]). The supervisory lobe reads the whole
   record *before* it sees the answer, specifically to avoid anchoring on
   A's framing [41]. The paired comparison against an answer-verifier arm
   (same model, same record, same schema) isolates exactly this difference.
2. **Evidence-gated interruption as the disagreement policy.** Instead of
   consensus, scores or a judge's preference, disagreement interrupts the
   clinician only when it is grounded in cited, verifiable record facts.
   Fabricated evidence disqualifies the objection. This connects generative
   supervision to the alert-fatigue literature in a testable way (false-hold
   rate on negative controls).
3. **Privacy-asymmetric lobes.** The supervisor's locality does two jobs. It
   keeps supervision on-premises, and it lets the supervisor act as the
   residual de-identifier for text about to leave. A rule-based
   de-identifier [27][28] cannot catch identifiers without structural cues.
   The trusted-monitor asymmetry [14] is applied here to data protection.
4. **Generative CDS without rule-base limits.** Unlike rule-based checkers,
   the supervisor can pick up hazards carried by free text (a positive home
   pregnancy test mentioned in a note, a cancer history plus night pain).
   The generative supervisor is expected to be *less* reliable than a
   curated rule base for well-encoded drug interactions. The two are
   complementary: rule outputs can be fed in as `[K#]` knowledge.

## Where the evidence stands

LLMs show strong clinical knowledge on examination-style benchmarks
[15][16][17] and also hallucinate in the medical domain [20]. Neither result
says whether a supervisory pass catches *omitted* hazards in realistic
records. That is the gap the study in `docs/EVALUATION.md` is built to
measure.

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

> Before submission, verify every reference against the publisher's record
> and format it to the target venue's style.
