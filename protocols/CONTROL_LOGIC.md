# Formal Control Logic

1. Freeze the original user query and supplied patient context for the run.
2. Start the independent B supervisory pass before B sees the final A answer.
3. Supply B with original context plus any additional information made available by runtime or tools.
4. Run A while preserving the observable execution and provenance trace.
5. B emits structured findings from the predefined failure taxonomy.
6. After A completes, B receives the exact A answer and observable trace and performs the final audit.
7. If B reports missing information, contradiction, or a material hazard, apply the explicit disagreement policy.
8. Apply the deterministic gate: PASS, WARN, REVISE, BLOCK, ESCALATE, or INSUFFICIENT_EVIDENCE.
9. Preserve the original audit trail if revision occurs.
10. Persist raw outputs, decisions, trace fingerprints, timing, privacy receipts, and errors.

The runtime does not require a fixed medical corpus or evidence-ID registry. Information may come from supplied context, tools, runtime retrieval, or other configured supervisory inputs.