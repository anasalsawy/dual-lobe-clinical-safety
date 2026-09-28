# Methods: computational specification

This document specifies the clinical Dual-Lobe proxy precisely enough to
re-implement or audit it. Every rule below has a direct counterpart in code,
cited in brackets, and a test in `tests/`.

## 1. Problem statement

A clinician submits a question *q* about a patient with record *R*. A
generative assistant produces an answer *a = A(q, R)*. The safety failure
this work targets is **omission**: *R* contains a fact that makes the
requested action unsafe or requires action anyway, and neither *q* nor *a*
mentions it. Examples are an NSAID asked about for a patient whose record
shows eGFR 28 on an ACE inhibitor and a diuretic, or a refill request when
the latest potassium is 6.4 mmol/L.

A verifier that checks *a* against *q* is **answer-conditioned**. It asks
"is this a good answer to the question?", so it inherits the question's
blind spot. The supervisory lobe here is **context-conditioned**. It reads
*R* in full, independently of *q*'s focus and before it sees *a*, and asks
"what in this record must the clinician know before acting?"

## 2. Components and information flow

| Component | Runs where | Sees | Produces |
|---|---|---|---|
| Privacy session *P* | in-process | raw *q*, *R* | de-identified view *V = (q', F)*; vault; receipt |
| Residual sweep *B₀* | **local** model | *V* (may still contain residual identifiers) | extra identifiers to tokenize |
| Primary lobe *A* (+ children) | any provider | *V* only, via the egress monitor | answer *a* (cites fact IDs) |
| Context scan *B₁* | **local** model | *V*, retrieved knowledge *K* (never *a*) | hazards *H₁* |
| Final audit *B₂* | **local** model | *V*, *K*, *H₁*, *a* | verdict *v*, findings *H₂* |
| Gate *G* | in-process, deterministic | *V*, *a*, *K*, *v*, *H₂* | release decision, interrupting findings, advisories |

`F = {F1: "path: text", ...}` is the record flattened into numbered facts
(`PrivacySession.build_view`). Identifier fields are removed entirely and a
date of birth becomes `age_years`. *A* and *B* reference the same fact IDs,
so citations are checkable.

Execution order (`engine.ClinicalDualLobeEngine.run`):

```
P.build_view(q, R) -> V
if B is local: V <- P.reapply(V after B0 sweep)       # sequential, before anything leaves
K <- retrieve(V)                                      # deterministic, local
concurrently:  a  <- A(V)          (remote allowed, egress-monitored)
               H1 <- B1(V, K)      (local, never sees a)
               [live B observes A's execution events]  (optional, local)
v, H2 <- B2(V, K, H1, a)                              # local
decision <- G(v, ground(H2))
display <- P.rehydrate(a, H2)                         # local, for the clinician only
P.destroy()                                           # always, in finally
```

Because *B₁* runs concurrently with *A*, the independent scan adds no
wall-clock latency on top of *A*. Only the final audit is sequential.

## 3. Formal control logic

### 3.1 Grounding (`control.ground_finding`)

A finding *h* = (kind, severity, statement, E_patient, quote, E_knowledge).
Let *S = {Q: q', A: a} ∪ F* and let *K* be the IDs retrieved in this run.
*h* is **grounded** iff all of the following hold:

1. every reference in E_patient is in *S*, and every reference in E_knowledge is in *K*;
2. the kind has the evidence it needs:
   - `unasked_hazard`, `answer_error`: at least one F#;
   - `missing_information`: at least one F# or Q;
   - `unsupported_claim`: A;
3. if a quote is given, its normalized form is a substring of at least one cited source.

A fabricated reference, citation or quote makes *h* ungrounded. That is
treated as evidence about the supervisor's own reliability, consistent with
the anti-deception protocol that B inherits from the generic runtime.

Duplicates (same kind, same evidence, same statement) are merged and keep
the most severe copy.

### 3.2 Effective verdict (`control.effective_verdict`)

* `GREEN` becomes `YELLOW` if any grounded finding exists or any handoff gap
  (missing / unverified / proof_requests) is open.
* `RED` becomes `YELLOW` unless a grounded `answer_error` or grounded
  critical finding exists. The supervisor cannot escalate without evidence.

### 3.3 Release gate (`control.decide`). First matching rule wins.

| # | Condition | Release | Clinician must acknowledge |
|---|---|---|---|
| 1 | an outbound call was refused by the privacy monitor | `BLOCKED` (nothing shown) | – |
| 2 | *A* produced no answer | `UNVERIFIED` | yes |
| 3 | no supervision configured (study baseline) | `UNSUPERVISED` | – |
| 4 | *B₂* failed or its output was unparsable | `UNVERIFIED`: fail closed; the answer is never labelled as checked | yes |
| 5 | ≥1 grounded critical/major finding, or effective verdict `RED` | `HOLD_FOR_CLINICIAN` | yes |
| 6 | effective verdict `YELLOW`, or any other finding | `RELEASE_WITH_ADVISORIES` | no |
| 7 | otherwise | `RELEASE` | no |

## 4. Disagreement policy

A and B disagree whenever B reports a finding that A's answer does not
address. The policy is:

1. **Neither lobe overrides the other.** B never rewrites, repairs or
   suppresses A's answer (inherited from the generic runtime's "B does not
   fix" rule). A never sees B's final audit. The clinician is the arbiter.
2. **Evidence-gated interruption.** A disagreement can interrupt the
   clinician (rule 5) only if it is grounded in cited patient facts and is
   rated critical or major. Ungrounded or minor objections are shown as
   advisories, visibly marked, and never block. This is the main control
   against false alarms and alert fatigue.
3. **Order of presentation.** On a hold, the interrupting findings are shown
   before the answer, each with the exact record entry it rests on,
   rehydrated for the clinician. The clinician can verify the claim in
   seconds rather than trusting either model.
4. **Failure is visible.** If B cannot complete, the result is `UNVERIFIED`,
   never a silent pass (rule 4).
5. **Independence before comparison.** B's scan is made without A's answer,
   so B's view is not anchored by A's. Only the audit compares the two.
6. **Early resolution (optional).** With live B enabled, B's challenges reach
   A through the generic runtime's non-blocking intervention channel while
   A is still working. A can then address a hazard in its own answer, and
   the final audit will not need to raise it.

## 5. Evidence retrieval

* **Patient evidence.** The record is flattened into numbered facts with
  stable paths, and every patient-specific claim by either lobe is expected
  to cite them. Citations are checked deterministically (§3.1).
* **Medical knowledge** (`knowledge.py`). An institution-supplied corpus
  (formulary monographs, label excerpts, local guidelines, as JSONL) is
  searched lexically with the question and every record fact as queries.
  The top snippets are placed in B's prompt as `[K1]…[Kn]`. Retrieval is
  deterministic and happens before the model call, so it does not depend on
  a small local model's tool-calling ability, and every snippet B saw is
  known. B may cite only those IDs.
* Without a corpus, B uses its trained knowledge and cites patient facts
  only. This configuration is recorded in the result.

## 6. Failure taxonomy

### 6.1 Failures of the primary lobe that the supervisor targets (`models.FindingKind`)

| Code | Failure | Example |
|---|---|---|
| `unasked_hazard` | The record contains a risk the question did not raise and the answer did not address | Clarithromycin asked about; record shows simvastatin |
| `missing_information` | A safe answer needs data the record does not contain | Vancomycin dose asked; no weight or renal function |
| `answer_error` | The answer is contradicted by the record, or clinically wrong for this patient | Recommends amoxicillin with documented penicillin anaphylaxis |
| `unsupported_claim` | The answer asserts a patient-specific fact the record does not support | "Renal function is normal" with no renal result on file |

Severity: **critical** means likely serious harm if acted on unaddressed;
**major** means it should change or condition the plan; **minor** means it
is worth noting and does not change the plan.

### 6.2 Failures of the system itself, and the control for each

| Failure | Control | Where |
|---|---|---|
| Supervisor misses a hazard | Independent context-conditioned scan plus audit; measured as sensitivity in the study | `engine`, `evaluation/score.py` |
| Supervisor false alarm | Evidence-gated interruption, severity rules, explicit "empty list is correct" instruction; measured on negative controls | `control.decide`, prompts |
| Supervisor fabricates evidence | Citation, quote and knowledge-ID verification; fabricated findings cannot interrupt | `control.ground_finding` |
| Supervisor output malformed or missing | Fail closed to `UNVERIFIED`; malformed items counted and reported | `engine.parse_review`, rule 4 |
| Supervisor verdict inflated or deflated | Effective-verdict rules (§3.2) | `control.effective_verdict` |
| Automation bias (clinician over-trusts) | B never edits A; findings show the source record entry; holds require acknowledgement; `GREEN` is defined as "no deception detected", never "correct" | `ClinicalResult.visible_text` |
| Alert fatigue | Only grounded critical/major findings interrupt; advisories are passive | `control.decide` |
| Identifier leaks to a remote model | De-identification, residual local sweep, destination-based egress monitor at two layers; measured by the leak probe in every study run | `privacy`, `egress`, `run_study.LeakProbe` |
| Supervisor itself sent off-site | B must resolve to a local destination; no cross-role failover for B; refuses to run otherwise | `locality.resolve_b_specs` |
| Identifier retention after use | Session keys destroyed in `finally`; no plaintext index; ephemeral memory | `PrivacySession.destroy`, `EphemeralMemoryStore` |
| Correlated error between lobes | Different conditioning (question vs whole record), no shared context before the audit, and ideally a different model (local B vs remote A) | architecture |

## 7. Analytical properties

These follow from the construction. They are verified by
`tests/test_gate_exhaustive.py` (G1–G3) and by the provider-boundary tests
(P1), and they state exactly what the empirical study still has to measure.

**Detection.** For a case whose record holds a hazard, let *M* be the event
that A's answer misses it and *D* the event that B raises a grounded
interrupting finding on it. The clinician is shown the hazard with probability

  P(surfaced) = P(¬M) + P(M) · P(D | M).

The supervisor's added value is exactly P(M)·P(D | M). It is zero only when
B always fails where A fails. The design therefore targets the *conditional*
detection P(D | M), and this is what separates it from an answer-conditioned
verifier. A verifier inherits the question's framing, so its misses are
expected to correlate with A's. B's context conditioning, its pre-answer
scan without A's output, and a different (local) model all aim to break that
correlation. The paired `dual_lobe` vs `answer_verifier` comparison estimates
the difference in P(D | M) with everything else held fixed.

**False alarms.**
- (G1) On any case, a hold happens only if a finding is grounded: it cites
  record entries that exist, with a quote that occurs in them. Ungrounded
  output contributes nothing to the hold rate (invariant I5).
- So every false hold is a *misjudgement of a real record entry*, never a
  fabricated one. The false-hold rate equals the rate at which B overrates a
  genuine fact as critical/major. That quantity is measured on negative
  controls, and a clinician can check each instance in seconds against the
  quoted entry.

**Fail-closed.**
- (G2) The probability that an unchecked answer is presented as checked is
  zero: any supervisor failure yields `UNVERIFIED` (invariant I2).
- (G3) Every grounded critical/major finding reaches the clinician
  (invariant I4), and no finding is silently dropped (invariant I7).

**Latency.** With the scan concurrent with A, wall-clock time is

  T = T_sweep + max(T_A, T_scan) + T_audit,

against T_A + T_verify for a post-hoc verifier. The extra cost over the
verifier baseline is T_sweep + max(0, T_scan − T_A) + (T_audit − T_verify).
It is reported per arm by `score.py`.

**Privacy.**
- (P1) For every identifier registered in the session (structured fields,
  pattern and cue detections, local-sweep additions), exposure to a remote
  destination is zero by construction. Every remote-bound payload is
  re-de-identified at two layers, and any failure refuses the call.
- Residual risk is confined to identifiers that are unregistered *and*
  missed by both the rules and the local sweep, plus quasi-identifiers. The
  leak probe measures this in every study run.
- After `destroy()`, any token or fingerprint that outlived the request is
  unresolvable and unlinkable (the keys no longer exist).

## 8. What is deliberately not claimed

* The supervisor does not make answers correct. It surfaces evidence-cited
  concerns for a clinician.
* `GREEN` means only that no contradiction or unsupported claim was detected
  from the available evidence.
* The benchmark labels are author-drafted and must be clinician-validated
  before any result is reported (see `docs/EVALUATION.md`).
