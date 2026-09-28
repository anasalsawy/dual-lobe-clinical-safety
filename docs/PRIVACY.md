# Patient-identity privacy

**Goal:** a remote model can do the clinical reasoning without learning who
the patient is. Every identifier used for the request is made unreadable
when the request ends.

## Why the two-lobe design matters for privacy

The lobes have different privacy positions, and that asymmetry is what makes
the guarantee practical:

* **Lobe B always runs locally**, on hardware the institution controls. It is
  the only model allowed to see text that has not yet been certified
  identifier-free. That lets B do what rules cannot: read the de-identified
  text *before it leaves* and point out identifiers that have no structural
  cue ("lives with Tomasz", "walks the dog in Riverside Park"). B's safety
  scan and audit never leave the premises either, so supervision adds no
  second external exposure.
* **Lobe A may be a large remote model**, because it only ever receives the
  de-identified view.

In clinical mode B is not allowed to fail over to A's remote provider
(`locality.resolve_b_specs`). If no local B is configured, the proxy refuses
to run.

## Pipeline

1. **Structured identifiers** (HIPAA Safe Harbor categories: names, contact
   details, addresses and sub-state geography, record, account, insurance,
   licence and device numbers, URLs, IPs, dates of birth). These are
   registered in the vault and dropped from the clinical view entirely (the
   minimum-necessary principle). A date of birth becomes `age_years`.
2. **Propagation.** Every registered identifier, and each part of a
   registered name, is found again in free text. Single name parts must be
   capitalized, so "may improve" is kept while "May Grant" is removed.
3. **Patterns.** Email, phone, SSN, labelled record numbers (must contain a
   digit), long numbers, URLs, IPs, state+ZIP, titled names ("Mr. Okoro"),
   and relation-cued names ("his daughter Priya").
4. **Dates** become offsets from the request's index date (`[DATE T-14d#…]`,
   `[DATE T-6mo#…]`). Intervals survive and calendar dates do not. Ages over
   89 become `90+`.
5. **Residual sweep** by local B (§ above). Only strings that occur verbatim
   in the outbound text are accepted, so a hallucinated "identifier" can
   never alter clinical content.
6. **Egress monitor.** Every outbound payload to a non-local destination is
   de-identified again against every active session, at two layers: the
   runtime's `run_one` (each task prompt) and CrewAI's `before_llm_call`
   hook (every message, including tool results that enter A's context
   mid-run). Any failure refuses the call (`BLOCKED`).
7. **Rehydration** happens only locally, only for the clinician's screen, and
   only for tokens this session issued. Forged tokens stay tokens.
8. **Destruction.** In a `finally` block the AES key and the HMAC key are
   overwritten and the vault is cleared.

## The vault

* No plaintext index: identifiers are recognized again through keyed
  HMAC-SHA256 digests of normalized word n-grams.
* Values are stored as AES-256-GCM ciphertext, with the token as associated
  data.
* Tokens are random per session: the same patient is `[NAME#3f9a1c]` in one
  request and something unrelated in the next.

After `destroy()`, anything that outlived the request (a token in a remote
provider's log, an audit fingerprint, a stray ciphertext) can no longer be
resolved or linked by anyone, including this process. This is
crypto-shredding.

## Other channels closed in clinical mode

* A's and B's persistent JSONL memories are replaced by per-request
  in-memory stores (`EphemeralMemoryStore`). Nothing about the patient is
  written to disk.
* CrewAI telemetry is disabled (`CREWAI_DISABLE_TELEMETRY`,
  `OTEL_SDK_DISABLED`).
* Study outputs contain only de-identified text.

## Privacy receipt

Every result carries a `PrivacyReceipt`. It records identifier counts by
category and detection source, how many outbound payloads were checked
(remote and local), how many were sanitized at egress, how many were
blocked, B's locality, whether the residual sweep ran, key destruction
time, a content-free audit log, and the limitations below.

## Limitations (also written into every receipt)

* Python cannot guarantee that transient `str` copies are wiped from process
  memory. The keys are overwritten, and the strings are garbage-collected
  normally.
* **Quasi-identifiers** in clinical narrative (a rare disease plus an age
  plus an occupation) are not removed by de-identification. That is a
  re-identification risk (Sweeney 2000), not a direct-identifier leak.
* The remote provider receives de-identified text. Its retention of that
  text is governed by the provider agreement.
* The deterministic audit (`evaluation/privacy_audit.py`) runs on
  author-written cases. That is a regression test, not an estimate of
  de-identification recall on real notes. Recall should be measured on a
  standard corpus such as the i2b2/UTHealth 2014 de-identification set
  (Stubbs & Uzuner 2015) before deployment.
* This is not a compliance certification.

## Measured so far (`results/privacy_audit.json`)

| Metric | Value |
|---|---|
| Cases | 29 |
| Identifiers planted | 115 |
| Removed by the deterministic layer | 114 |
| Leaked defects | 0 |
| Left for the local-B sweep (by design) | 1 ("Riverside Park") |
| Clinical values reaching A unchanged | 97 / 97 |
| Sessions crypto-shredded | 29 / 29 |

End-to-end tests (`tests/test_clinical_engine.py`) intercept every payload
at the provider boundary. They check that no planted identifier reaches the
remote lobe, and that the residual sweep and all B calls go only to the
local model.
