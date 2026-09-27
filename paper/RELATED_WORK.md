# Related Work

This document is a working literature synthesis for the manuscript. It is not
yet a systematic review. Claims of novelty must remain limited to distinctions
that survive the formal literature search and the A0/A1/A2/A3 ablations.

## 1. Self-refinement and self-critique

Madaan et al. introduced **Self-Refine**, in which the same LLM generates an
initial output, provides feedback on that output, and iteratively refines it.
This is an important baseline because it directly tests whether extra inference
alone is sufficient.

Reference:
Madaan A, Tandon N, Gupta P, et al. Self-Refine: Iterative Refinement with
Self-Feedback. arXiv:2303.17651 (2023).
https://arxiv.org/abs/2303.17651

Relation to this project:
- Self-Refine uses a single model as generator, feedback provider, and refiner.
- Dual-Lobe deliberately separates A from an independent supervisory B.
- A1 in this repository is the self-review comparator; A2 tests architectural
  independence beyond self-review.

## 2. Verification chains

Dhuliawala et al. proposed **Chain-of-Verification (CoVe)**: a draft is
generated, verification questions are planned, those questions are answered
independently, and a final response is produced. CoVe demonstrates that
independent verification substeps can reduce hallucination.

Reference:
Dhuliawala S, Komeili M, Xu J, et al. Chain-of-Verification Reduces
Hallucination in Large Language Models. arXiv:2309.11495 (2023).
https://arxiv.org/abs/2309.11495

Relation to this project:
- CoVe verifies a drafted answer through a staged single-system procedure.
- Dual-Lobe B forms a safety representation *before* seeing A's answer, then
  audits A afterward.
- The target is not only factual hallucination but omitted context,
  contraindications, interactions, urgent red flags, provenance, and privacy.

## 3. Multi-agent debate

Du et al. evaluated multiple LLM instances that propose and debate answers
over multiple rounds to improve reasoning and factuality.

Reference:
Du Y, Li S, Torralba A, Tenenbaum JB, Mordatch I. Improving Factuality and
Reasoning in Language Models through Multiagent Debate. arXiv:2305.14325
(2023).
https://arxiv.org/abs/2305.14325

Relation to this project:
- Debate is generally symmetric and aims at convergence or a common answer.
- Dual-Lobe is intentionally asymmetric: A executes; B supervises.
- B need not persuade A or reach consensus.
- A deterministic gate can block release even when A and B agree if evidence
  is insufficient.

## 4. Separate learned verifiers

Baek et al. proposed **Knowledge-Augmented Language Model Verification
(KALMV)**, using a separate smaller language model trained to detect retrieval
and generation errors in knowledge-augmented LMs.

Reference:
Baek J, Jeong S, Kang M, Park JC, Hwang SJ. Knowledge-Augmented Language Model
Verification. arXiv:2310.12836 (2023).
https://arxiv.org/abs/2310.12836

This is close prior art and must be discussed prominently.

Relation to this project:
- KALMV establishes the value of a separate verifier rather than pure
  self-verification.
- Dual-Lobe extends the verification target from retrieval/generation
  factuality to patient-context omission, clinical hazards, execution
  provenance, and information-handling/privacy obligations.
- Clinical B is local-only and can be frozen as a known fine-tuned guardian.
- The release decision is owned by deterministic control logic rather than the
  verifier itself.
- These differences are hypotheses about architectural value and require
  empirical validation; they should not be presented as established superiority.

## 5. Knowledge-enhanced verify-and-edit

Zhao et al. proposed Verify-and-Edit, which post-edits reasoning chains using
external knowledge to improve factuality.

Reference:
Zhao R, Li X, Joty S, Qin C, Bing L. Verify-and-Edit: A Knowledge-Enhanced
Chain-of-Thought Framework. arXiv:2305.03268 (2023).
https://arxiv.org/abs/2305.03268

Relation:
The present system also uses external evidence, but separates the verifier from
the generator and evaluates evidence retrieval as an explicit A3 ablation.

## 6. Constitutional and rule-based AI supervision

Bai et al. showed that model behavior can be shaped by critique/revision and AI
feedback under an explicit constitution.

Reference:
Bai Y, Kadavath S, Kundu S, et al. Constitutional AI: Harmlessness from AI
Feedback. arXiv:2212.08073 (2022).
https://arxiv.org/abs/2212.08073

Relation:
Dual-Lobe likewise uses explicit supervisory rules, but this clinical project
focuses on inference-time independent oversight and deterministic gating rather
than training a generally harmless assistant through RLAIF.

## 7. Medical guardrails

Hakim et al. implemented hard and soft guardrails for pharmacovigilance,
including consistency checks and uncertainty signaling in a safety-critical
medical workflow.

Reference:
Hakim JB, Painter JL, Ramcharran D, et al. The need for guardrails with large
language models in pharmacovigilance and other medical safety critical
settings. Scientific Reports. 2025;15:27886.
doi:10.1038/s41598-025-09138-0

Relation:
- This work demonstrates the value of task-specific deterministic and semantic
  guardrails in medicine.
- Dual-Lobe should be framed as complementary rather than a replacement:
  deterministic controls remain appropriate wherever a rule can be specified.
- B targets open-ended hazards that are difficult to enumerate exhaustively,
  while the gate/privacy membrane enforce hard constraints.

## 8. Retrieval-augmented generation in biomedicine

Liu, McCoy, and Wright performed a systematic review/meta-analysis of RAG in
biomedicine and reported improved performance over baseline LLMs, while
emphasizing system-level, knowledge-level, and integration-level development.

Reference:
Liu S, McCoy AB, Wright A. Improving large language model applications in
biomedicine with retrieval-augmented generation: a systematic review,
meta-analysis, and clinical development guidelines. J Am Med Inform Assoc.
2025;32(4):605-615. doi:10.1093/jamia/ocaf008.

Additional reviews:
Amugongo LM, Mascheroni P, Brooks S, Doering S, Seidel J.
Retrieval augmented generation for large language models in healthcare:
A systematic review. PLOS Digital Health. 2025;4(6):e0000877.
doi:10.1371/journal.pdig.0000877.

Miao Y, Zhao Y, Luo Y, Wang H, Wu Y. Improving Large Language Model
Applications in the Medical and Nursing Domains With Retrieval-Augmented
Generation: Scoping Review. J Med Internet Res. 2025;27:e80557.
doi:10.2196/80557.

Relation:
RAG improves grounding but does not by itself establish independent
supervision. A2 vs A3 is designed to separate the effect of supervisory
independence from the incremental effect of retrieval.

## 9. Clinical LLM safety and harmful recommendations

Omar et al. evaluated adversarial hallucination attacks across multiple LLMs
using 300 physician-validated simulated vignettes and found substantial
susceptibility; mitigation prompting reduced but did not eliminate the problem.

Reference:
Omar M, Sorin V, Collins JD, et al. Multi-model assurance analysis showing
large language models are highly vulnerable to adversarial hallucination
attacks during clinical decision support. Communications Medicine. 2025;5:330.
doi:10.1038/s43856-025-01021-3.

A 2026 retrospective evaluation of an LLM-based clinical decision support
system across 16 Kenyan primary-care clinics found both beneficial risk
mitigation and actively harmful recommendations, underscoring the need for
local guardrails and prospective safety evaluation.

Reference:
Safety of a large language model-based clinical decision support system in
African primary healthcare. Nature Health. 2026.
doi:10.1038/s44360-026-00082-5.

Relation:
These studies motivate measuring both prevented harm and newly introduced harm.
The present benchmark therefore includes matched negative controls,
false-positive rates, unsafe-release rates, and unnecessary-block rates.

## 10. Medication safety and clinical co-pilots

Ong et al. evaluated LLM-based medication safety support across 16 specialties
and compared LLM-alone, pharmacist-plus-LLM, and pharmacist-alone conditions.

Reference:
Ong JCL, Jin L, Elangovan K, et al. Large language model as clinical decision
support system augments medication safety in 16 clinical specialties.
Cell Reports Medicine. 2025;6(10):102323.
doi:10.1016/j.xcrm.2025.102323.

Relation:
This supports the broader premise that clinical safety evaluation must assess
how AI supervision interacts with existing human decision processes. It does
not establish the specific dual-lobe architecture proposed here.

## 11. Current evidence gap targeted by this project

The literature already contains:
- self-critique/refinement;
- staged verification;
- multi-agent debate;
- separate learned verifiers;
- external-knowledge verification;
- deterministic/semantic medical guardrails;
- clinical RAG;
- clinical decision-support evaluations.

Accordingly, the manuscript must NOT claim novelty merely for:
- using two LLM calls;
- adding a critic;
- using a verifier;
- using retrieval;
- using guardrails.

The narrower hypothesis tested here is whether a **persistent independent
clinical supervisory pathway** that:
1. forms a pre-answer patient-context safety representation;
2. remains separate from an arbitrary provider-facing generator;
3. observes the generator's execution/provenance;
4. audits material claims and omitted hazards;
5. is locally hosted as a known guardian;
6. supervises patient-data handling as well as clinical content; and
7. feeds a deterministic release gate,

provides measurable benefit over single-model generation, self-review, and the
same architecture without evidence retrieval.

That distinction is a testable research question, not a conclusion.
