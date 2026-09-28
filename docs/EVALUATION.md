# Evaluation

The reviewer asked for evidence that the supervisory lobe (1) improves
safety, (2) detects omitted contraindications reliably, and (3) avoids
creating new false alarms and automation risks. This document states the
hypotheses, the design that tests them, the evidence already produced, and
exactly what remains to be run.

## Evidence produced so far

| Kind | What | Result | Reproduce |
|---|---|---|---|
| Analytical (exhaustive verification) | Release-gate safety invariants I1–I7 (privacy dominates; fail closed; no interruption without grounded evidence; every grounded critical/major finding interrupts; ungrounded findings never interrupt; a clean release needs no findings and GREEN; no finding silently dropped) over the whole enumerated input space | 50,568 / 50,568 configurations satisfy all invariants | `pytest tests/test_gate_exhaustive.py` |
| Empirical (deterministic) | Identifier leakage and clinical-content preservation in exactly what the remote lobe receives, 133 cases | 626 identifiers planted; 624 removed by the deterministic layer; 0 defects; 2 left for the local sweep by design; 385/385 clinical values preserved; 133/133 sessions crypto-shredded | `python evaluation/privacy_audit.py` |
| Integration (scripted models at the provider boundary) | No planted identifier reaches the remote lobe; every B call and the residual sweep go only to the local model; a remote B is refused before anything leaves; malformed supervisor output fails closed; fabricated evidence cannot interrupt; B never alters A's answer | all pass | `pytest tests/test_clinical_engine.py tests/test_clinical_privacy.py` |
| Harness validation | Every study arm runs end to end, the leak probe works, scoring and blinded export work | pass | `pytest tests/test_evaluation.py` |

**Not yet produced: model-performance results.** Sensitivity for omitted
hazards and the false-hold rate depend on the actual A and B models. They
must be measured with them. No number for them is claimed anywhere in this
repository.

## Hypotheses

* **H1 (omission detection).** On cases whose record contains a hazard the
  question does not raise, the `dual_lobe` arm surfaces the hazard more often
  than `a_only`, *and more often than `answer_verifier`* (same model, same
  record, same schema, but answer-conditioned). The second comparison
  isolates the contribution of context conditioning.
* **H2 (false alarms).** On negative controls, the `dual_lobe` false-hold
  rate is low (pre-specify an acceptable ceiling with clinicians, e.g.
  ≤ 10 %) and not higher than `answer_verifier`'s.
* **H3 (privacy).** Zero planted identifiers reach any remote destination in
  any arm, measured by the leak probe on every run.
* **H4 (fail-closed).** Every supervisor failure is reported as
  `UNVERIFIED`. None becomes `RELEASE`. (Guaranteed analytically by I2; the
  study reports how often it happens.)

## Design

* **Cases.** `benchmarks/clinical/cases.json` (v2.0) has 133 synthetic
  cases: 79 unasked hazards across drug–drug, drug–disease, allergy,
  pregnancy, childbearing potential and lactation, renal and hepatic
  dosing, pharmacogenomics, QT prolongation, paediatric, older-adult,
  device, boxed-warning, red-flag and critical-result domains; 6
  missing-information cases; and 48 negative controls. Of those, 8 are
  independent controls, several with deliberate distractors (an irrelevant
  sulfonamide allergy with cephalexin, amlodipine with atorvastatin). The
  other 40 are **matched twins**: the same question as a hazard case with
  only the hazard fact removed. Each case plants identifiers in structured
  fields and in narrative and records the clinical basis of its label. See
  `benchmarks/clinical/DATASHEET.md` for provenance.
* **Matched-pair discrimination.** The share of runs that hold the hazard
  version and not its twin. This shows the supervisor reacts to the hazard
  fact itself, not to the question or to general caution.
* **Provenance.** Every output row records the SHA-256 of the case file,
  the code commit and the model identifiers.
* **Arms.** `a_only`, `answer_verifier`, `dual_lobe`, and optionally
  `dual_lobe_live`. Models, record view and retrieval are held constant
  across arms.
* **Repeats.** At least 3 per case and arm (model sampling is not
  deterministic). Outcomes are paired by (case, repeat).
* **Primary endpoint (expert evidence).** Two independent clinicians, blind
  to arm, rate each output from `score.py --export-adjudication`: gold issue
  surfaced (Y/N), false alarm (Y/N), harmful if followed (Y/N).
  Disagreements go to a third clinician. Report agreement (Cohen's κ).
  `evaluation/adjudication.py` computes κ, lists the disagreements, applies
  the tie-break and reports adjudicated per-arm rates with Wilson intervals.
* **Screening endpoint (automated).** `score.py`: surfaced = A names the gold
  issue, or the gate raises an interrupting grounded finding citing a gold
  fact or naming a gold term. It is useful for iteration, but it is not the
  endpoint.
* **Statistics.** Proportions with Wilson 95 % intervals. Paired arm
  comparisons with the exact McNemar test. Latency, model-call counts and
  repeat consistency (share of cases with the same outcome in every repeat)
  reported per arm.

## Before running: validate the gold labels

The gold labels were drafted from widely established, label-level facts
(`gold.summary` in each case). They are author-drafted. Before any result is
reported, have at least one independent clinician confirm or correct each
label and add cases from their own practice. Freeze the case file (commit
hash) before the run.

## Sample size

With 85 hazard cases and 48 negative controls, each run 3 times, the
paired design can detect moderate differences between arms (roughly 15
percentage points or more, depending on how often arms disagree), not only
large ones. Repeats are not independent samples, so report the per-case
results and treat the case, not the run, as the unit for any confirmatory
claim. External validity still requires real, de-identified omission
incidents (for example, local incident reports). Pre-register the analysis
by freezing the case-file hash before the run.

## How to run

```bash
pip install -e .
# Lobe B: local (required). Example with Ollama:
ollama pull llama3.1:8b          # or a medically tuned local model
export DUAL_LOBE_B_MODEL=ollama/llama3.1:8b
# Lobe A: any provider
export DUAL_LOBE_A_MODEL=<provider/model>  DUAL_LOBE_A_API_KEY=<key>

python evaluation/privacy_audit.py
python evaluation/run_study.py --arms a_only answer_verifier dual_lobe --repeats 3
python evaluation/score.py results/study_<stamp>.jsonl --export-adjudication results/adjudication
# two clinicians fill copies of adjudication_sheet.csv independently, then:
python evaluation/adjudication.py results/adjudication/adjudication_key.json rater1.csv rater2.csv [--tiebreak rater3.csv]
```

**Synthetic-data variant with hosted APIs.** The benchmark contains no real
patient data, so the model study may also be run with B on a hosted API.
This environment can reach Google's and Anthropic's APIs. Disclose the
configuration in the manuscript; locality enforcement itself is verified by
the integration tests.

```bash
export DUAL_LOBE_A_MODEL=gemini/<model-id>          # reads GEMINI_API_KEY
export DUAL_LOBE_B_MODEL=anthropic/<model-id>       # reads ANTHROPIC_API_KEY (a different family from A)
export DUAL_LOBE_CLINICAL_B_LOCALITY=prefer         # synthetic data only; recorded in every result row
python evaluation/run_study.py --arms a_only answer_verifier dual_lobe --repeats 3
```

Configuration used for the reported run (free tiers of two providers, so A
and B come from different model families and draw on separate quotas; B is
open-weight and could be served locally in deployment). crewAI has no native
Groq provider, so B uses the OpenAI-compatible endpoint:

```bash
export DUAL_LOBE_A_MODEL=gemini/gemini-3.5-flash-lite  DUAL_LOBE_A_API_KEY=$GEMINI_API_KEY
export DUAL_LOBE_B_MODEL=openai/openai/gpt-oss-120b    DUAL_LOBE_B_API_KEY=$GROQ_API_KEY
export DUAL_LOBE_B_BASE_URL=https://api.groq.com/openai/v1
export DUAL_LOBE_CLINICAL_B_LOCALITY=prefer
export DUAL_LOBE_CROSS_ROLE_FAILOVER=false   # B must never fall back to A's model
export DUAL_LOBE_A_RPM=10 DUAL_LOBE_B_RPM=25 DUAL_LOBE_B_TPM=8000 DUAL_LOBE_RATE_SAFETY=1
export DUAL_LOBE_RETRY_ROUNDS=6 DUAL_LOBE_RETRY_MAX_SECONDS=60
```

Free-tier quotas are per model and per day (for example, 20 requests/day for
`gemini-3.8-flash` at the time of the run), so check them before choosing A.
Run one process: provider rate limits are per account, and the runtime's
rate controller is per process.

The study writes only de-identified outputs. The adjudication key (arm per
item) is written separately so raters stay blind.

## Threats to validity

* The cases are synthetic and short. Real records are longer and noisier,
  which may lower both sensitivity and precision.
* Term-based automated scoring can over-count (a term mentioned in passing)
  or under-count (a hazard described with a synonym). This is why clinician
  adjudication is primary.
* A and B may share failure modes if they are the same model family. Report
  the models used, and prefer different families.
* The benchmark author also wrote the system. Clinician-contributed cases and
  a frozen case file reduce this bias.
