# Formal Control Logic v0.1

1. Freeze original user query and supplied patient context.
2. Run A on the task.
3. Independently run B on the original query + patient context + allowed evidence.
4. B emits structured findings from the frozen taxonomy.
5. Resolve every cited evidence ID against the frozen evidence store.
6. Reject ungrounded material supervisory claims.
7. Apply the deterministic gate:
   PASS / WARN / REVISE / BLOCK / ESCALATE / INSUFFICIENT_EVIDENCE.
8. If revision is permitted, A receives the specific safety obligation and retries.
9. Re-evaluate the revised answer without deleting the original audit trail.
10. Persist raw outputs, evidence IDs, decisions, timing, token use, and errors.

The primary scientific comparison is between architectures, not between
hand-picked outputs. All experimental arms must see the same benchmark cases.
