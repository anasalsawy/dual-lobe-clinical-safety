# Related Work

The reviewer asked that the proposed supervisory architecture be situated
against existing verifier and supervisory approaches. This section therefore
keeps the comparison narrow and architectural.

## Verifier and supervisory approaches

Prior work has explored self-critique, staged verification, separate verifier
models, and multi-model review. Examples include Self-Refine, Chain-of-
Verification, Knowledge-Augmented Language Model Verification, and multi-agent
debate.

These works establish that verification and model-to-model checking are not new
in themselves. The purpose of citing them here is to clarify how the present
system is organized, not to claim that any one paper is the uniquely closest
precedent.

The Dual-Lobe clinical system differs in the specific flow being studied:
- B is a persistent supervisory pathway rather than an occasional critique step;
- B forms an independent view of the original patient/context before seeing A's
  final answer;
- B later receives the observable A/tool execution trace and final answer;
- disagreement is resolved by explicit runtime policy rather than informal
  model consensus;
- B can be supplied with additional context or information through the runtime
  when needed;
- the implementation includes patient-data handling and privacy supervision.

## Clinical safety context

Medical-LLM safety work has shown the importance of guardrails, human review,
and measuring both prevented errors and newly introduced harms. These studies
motivate the clinical evaluation but are not treated as direct architectural
equivalents of Dual-Lobe.

## Scope of the comparison

The manuscript should make a concise comparison with representative verifier
and supervisory systems and explain the differences in control flow, context
visibility, and disagreement handling. It should not claim that verifier
models, retrieval, guardrails, or multi-model interaction are themselves novel.
