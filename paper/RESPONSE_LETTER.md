# Response to the Reviewer

Dear Reviewer,

Thank you for a careful and constructive review. You recognised the core
idea: a clinician may omit an important question, so a safety layer should
examine patient context proactively rather than only verify the literal
answer. You also identified precisely what the manuscript lacked to turn
that idea into science. We have rebuilt the work around your comments.
Below, each point is quoted and followed by our response and where to find
it. A requirement-by-requirement table with implementation status is in
`docs/REVIEWER_RESPONSE.md` of the accompanying repository.

---

> *"there is no formal control logic"*

The revised manuscript (§4) specifies the control logic formally. It has
three parts:

- a **grounding predicate**: a supervisory finding counts only if its cited
  record facts exist, it cites what its kind requires, and its quote occurs
  verbatim in the cited source;
- **effective-verdict rules**: no GREEN while grounded findings or evidence
  gaps remain, and no RED without grounded support;
- a **seven-rule release gate** (Table 2).

The gate is deterministic code with no model involvement. We verified it
exhaustively. Across all 50,568 configurations of its input space, seven
safety invariants hold (§10.1). These include that no ungrounded objection
can interrupt, that every grounded critical/major finding does, and that a
failed check can never be presented as passed.

> *"[no] evidence retrieval mechanism"*

The patient record is flattened into numbered facts with stable paths.
Every patient-specific claim by either lobe must cite them, and supervisory
findings must include a verbatim quote, which is machine-checked. Medical
knowledge is retrieved deterministically from an institution-supplied
corpus before the supervisory call. It is presented as numbered snippets,
and only retrieved snippet IDs may be cited (§5).

> *"[no] disagreement policy"*

Neither component overrides the other. The supervisor never rewrites the
answer, and the clinician arbitrates. A disagreement may interrupt the
clinician only if it is evidence-grounded and rated critical or major;
other objections appear as passive advisories. On an interruption, the
finding and its source record entry are shown before the answer. A
supervisory failure is always visible as UNVERIFIED. The supervisor forms
its view before seeing the answer, to avoid anchoring (§4).

> *"[no] failure taxonomy"*

We define four primary-lobe failure kinds: unasked hazard, missing
information, answer error and unsupported claim. Each is rated critical,
major or minor, and together they form the supervisor's machine-checked
output schema. We also list twelve system-level failure modes, including
supervisor miss, false alarm, fabricated evidence, automation bias, alert
fatigue, privacy leakage and correlated error, each with its control (§7).

> *"[no] implementation"*

The complete system is implemented and available in the accompanying
repository, with 92
automated tests in continuous integration. The tests include end-to-end
tests that intercept every payload at the model-provider boundary.

> *"[no] comparison with existing verifier and supervisory approaches"* and
> *"The lack of any references"*

§2 and Table 1 compare the approach with self-correction,
chain-of-verification, trained verifiers, LLM judges, guardrails,
multi-agent debate, clinical multi-agent systems, AI-control trusted
monitoring and rule-based CDS. We cite 42 references and state four
distinctness claims. The comparison is also executable: the evaluation
includes a conventional answer-verifier arm that uses the same model,
record and output schema as our supervisor. This isolates the effect of
conditioning the supervisor on the whole context rather than on the answer.

> *"no empirical, simulated, analytical, or expert evidence showing that the
> supervisory lobe improves safety, detects omitted contraindications
> reliably, or avoids creating new false alarms and automation risks"*

We now provide the following.

- **Analytical evidence** (§8, §10.1).
  - A decomposition of detection, P(surfaced) = P(¬M) + P(M)·P(D | M),
    showing exactly what supervision adds and what the comparison arm must
    measure.
  - A false-alarm property: every false hold is a misjudgement of a real,
    quoted record entry, never a fabrication.
  - Exhaustive verification of the gate.
- **Empirical privacy evidence** (§10.2). A deterministic audit of 29 cases
  with 115 planted identifiers: no deterministic leaks, all clinical values
  preserved, all session keys destroyed.
- **Simulated evidence** (§10.2). Integration tests with scripted models
  exercise every decision path at the provider boundary.
- **A pre-specified comparative study with expert evidence** (§9). It
  comprises:
  - a 29-case omission benchmark across 12 clinical domains, with negative
    controls designed to provoke false alarms;
  - three paired arms with repeated runs;
  - sensitivity, false-hold rate, repeat consistency and leak measurements;
  - blinded adjudication by two clinicians with Cohen's κ and a third-rater
    tie-break.

  Model-performance results will be reported in Table 4 exactly as measured.

We have kept the claims narrow. GREEN means only that no contradiction or
unsupported claim was detected. The supervisor does not make answers
correct. It surfaces evidence-cited concerns for a clinician.

**Additional revision.** We also addressed patient privacy, which we
consider a precondition for clinical use. The supervisory lobe must run
locally. The answering model receives only a de-identified, date-shifted
view. Every outbound payload is monitored and fails closed, and each
request ends with the destruction of its encryption keys (§6).

We are grateful for comments that materially improved the work.

Sincerely,
The author
