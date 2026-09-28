# Reporting-guideline alignment

Two reporting guidelines fit this study:

* **DECIDE-AI** (Vasey et al., Nat. Med. 2022) covers the early-stage
  clinical evaluation of AI decision support. It applies because this is a
  pre-deployment evaluation of a decision-support safety layer.
* **TRIPOD-LLM** (Gallifant et al., Nat. Med. 2025) covers studies that use
  large language models.

The tables map the items most relevant to a pre-clinical, in-silico
evaluation to where they are addressed. Items that need a live clinical
setting (for example, user-interaction logs in practice) are marked out of
scope for this stage and are stated as such in the manuscript's
limitations.

## DECIDE-AI (selected items)

| Item | Where addressed |
|---|---|
| Intended use, users and clinical pathway | Manuscript §1, §3; README (research use only) |
| Description of the AI system and its version | Manuscript §3–§6; `run_study.provenance` (code commit, models) |
| Input data and pre-processing | Manuscript §6 (de-identification); METHODS §2 (record flattening) |
| Human–AI interaction and output presentation | METHODS §4 (disagreement policy, findings shown first with their source entry, acknowledgement) |
| Safety and errors: identification and reporting | METHODS §6 (failure taxonomy); release gate; UNVERIFIED and BLOCKED states |
| Handling of AI failures or malfunctions | Fail closed (gate rule 4, invariant I2) |
| Evaluation participants (clinician raters) and blinding | EVALUATION (two blinded raters, third-rater tie-break, κ) |
| Comparator | `answer_verifier` and `a_only` arms |
| Outcomes and their definitions | EVALUATION endpoints; `score.py` docstring |
| Human factors and usability | Out of scope at this stage (future user study; stated) |

## TRIPOD-LLM (selected items)

| Item | Where addressed |
|---|---|
| LLM names, versions, providers, access dates | Recorded per row (`provenance.a_model`, `b_model`); report access dates in the manuscript |
| Prompts, verbatim | `src/dual_lobe_clinical/prompts.py` (released) |
| Inference parameters and repeats | `.env.example` (token budgets); `--repeats` (≥3) |
| Data source, provenance, synthetic status | `benchmarks/clinical/DATASHEET.md` |
| Data leakage / contamination | Benchmark is newly written, not public before the run; hash frozen |
| Annotation process for reference standard | DATASHEET (author-drafted, clinician-validated); EVALUATION |
| Evaluation metrics with uncertainty | Wilson intervals, exact McNemar, κ (`score.py`, `adjudication.py`) |
| Handling of output parsing failures | `malformed_items` counted; UNVERIFIED on unparsable output |
| Privacy and data protection | docs/PRIVACY.md; leak probe in every run |
| Code and data availability | Repository |
| Limitations and generalisability | Manuscript §12; DATASHEET limitations |
