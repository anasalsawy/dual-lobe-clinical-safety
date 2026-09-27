# Patient Data Privacy and Inference-Egress Protocol v0.1

## Principle

Clinical reasoning and patient confidentiality are separate safety obligations.
A medically correct answer is not acceptable if obtaining it required unnecessary
or uncontrolled disclosure of patient-identifying information.

The privacy function therefore sits at the same top-level proxy boundary as the
dual-lobe safety function.

## Architecture

RAW CLINICAL INPUT
        |
        v
DETERMINISTIC PRIVACY MEMBRANE
- detect direct identifiers
- minimize/tokenize before inference
- enforce provider policy
- prohibit raw persistence in study artifacts
        |
        +--------------------+
        |                    |
        v                    v
      LOBE A               LOBE B
  clinical execution    independent safety/privacy oversight
        |                    |
        +---------+----------+
                  v
        SANITIZED TRACE AUDIT
                  |
                  v
      CLINICAL + PRIVACY RELEASE GATES

## Why B remains important

The privacy membrane itself is deterministic because a remote B cannot protect
data that was already disclosed to B. B instead provides independent oversight
of the *use* of the minimized data and the observable run:

- challenge unnecessary data use;
- inspect tool/delegation provenance for attempted disclosure;
- detect claims that patient data were deleted or protected without proof;
- verify that A did not route sensitive data through an unauthorized path;
- preserve a privacy objection even when the clinical answer is correct.

This avoids self-verification by the same model that consumed the data.

## Assurance boundaries

The system may truthfully assert:
- which direct identifiers the proxy detected and removed;
- that only the sanitized payload was passed through the guarded inference path;
- whether raw inputs were intentionally persisted by this runtime;
- what provider privacy assurances were configured;
- which observable trace was audited.

The system MUST NOT assert, without external evidence:
- that a remote model provider physically erased every copy;
- that provider-side training/retention did not occur;
- that Python process memory was cryptographically zeroized;
- that simple tokenization alone constitutes formal HIPAA de-identification.

Provider-side assurances are recorded as attestations, not inferred facts.

## Publication metrics

The study should measure:
- identifier-detection recall/precision on a dedicated privacy dataset;
- raw-identifier egress rate;
- privacy-policy violation interception rate;
- false-positive redaction rate;
- clinical information preservation after minimization;
- privacy-gate latency overhead;
- provider-assurance coverage;
- unsupported deletion/privacy claims by A or B.
