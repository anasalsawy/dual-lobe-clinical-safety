# Literature Search Protocol v0.1

The current RELATED_WORK.md is a structured seed, not a systematic review.

Before manuscript submission, perform a reproducible literature search.

## Databases

At minimum:
- PubMed/MEDLINE
- IEEE Xplore
- ACM Digital Library
- arXiv
- Google Scholar or Scopus/Web of Science if institutionally available

## Concept groups

Search combinations of:
1. "large language model" OR LLM
2. verifier OR verification OR critique OR self-reflection OR self-refine
3. multi-agent OR debate OR supervisor OR oversight
4. guardrail OR safety layer OR hallucination mitigation
5. retrieval augmented generation OR RAG
6. clinical OR medical OR healthcare OR patient safety
7. contraindication OR medication safety OR clinical decision support
8. privacy OR protected health information OR patient data

## Inclusion

Include work that materially informs one or more of:
- separate-model verification;
- self-verification;
- multi-agent critique;
- deterministic or semantic guardrails;
- clinical RAG;
- clinical LLM safety evaluation;
- patient-data governance for LLM systems.

## Extraction fields

For every included work:
- citation
- publication status
- domain
- architecture
- whether verifier is independent
- whether verification occurs before/after draft
- external evidence use
- clinical context use
- execution/provenance visibility
- decision/gating mechanism
- privacy handling
- evaluation dataset
- false-positive measurement
- human/expert adjudication
- key limitations

## Novelty discipline

A contribution may be claimed only after the extraction table shows that the
exact combination is not already established in prior work.

Absence from this seed document is not evidence of novelty.
