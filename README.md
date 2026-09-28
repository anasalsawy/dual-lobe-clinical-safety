# Dual-Lobe Clinical Safety

Research implementation of a simple planner-executor Dual-Lobe architecture.

## Core architecture

The clinical runtime deliberately does not assume that the AI is answering a
physician's question. The incoming task may be a question, command, retrieval,
creation, update, send action, or another tool-mediated job.

- **Lobe A** is the reasoning and user-facing lobe. It understands the user's
  goal and produces the complete provisional plan. A does not own execution
  tools.
- **Lobe B** is the local execution lobe. It owns tools and local clinical data,
  executes A's plan, and continuously judges whether that plan still makes
  sense against reality.
- The A-authored plan is held by deterministic code as the current execution
  contract. B cannot silently rewrite, drop, or substitute plan steps.
- The A<->B channel remains available during execution. If B discovers that the
  plan is invalid, irrelevant, impossible, or incomplete, B calls A. A may
  return a revised complete plan, which deterministically becomes the new
  contract.
- B may immediately parallelize plan steps that A marked independent. This is
  intended to recover wall-clock time introduced by the two-lobe interaction.
- When execution finishes, A receives the final plan plus B's execution output
  and observable control/execution record, critiques whether execution actually
  fulfilled the plan, and produces the user-facing response.

In compact form:

```
USER
  |
  v
A: think + full plan
  |
  v
deterministic current-plan contract
  |
  v
B: challenge + execute + parallelize
  |              |
  |<---- A <-----|  plan revision whenever needed
  |
  v
execution results
  |
  v
A: check execution + answer user
```

## Clinical privacy boundary

B uses the local `B_CLINICAL` model role and is restricted by the provider
layer to a loopback/local endpoint. Raw clinical context is available to local
B for execution. Before information is sent to remote A, direct identifiers
are replaced with run-scoped opaque tokens backed by a local AES-256-GCM vault.
B execution material is sanitized again before A's final review.

The privacy mechanism is a minimization boundary, not a claim of regulatory
compliance or physical memory zeroization.

## Plan contract

A returns one compact structure:

```json
{
  "goal": "...",
  "constraints": ["..."],
  "steps": [
    {
      "id": "S1",
      "action": "...",
      "parallelizable": true,
      "depends_on": []
    }
  ],
  "success_condition": "..."
}
```

The structure exists only to keep the plan from silently dissolving during
execution. It is not a clinical decision taxonomy or a separate safety layer.

## Relationship between the lobes

The adversarial relationship follows naturally from role separation:

- B does not blindly trust A's plan; it tests the plan against actual data,
  tools, failures, and changing execution state.
- A does not blindly trust B's execution; it checks the execution material
  against the final plan before reporting completion.
- They must cooperate because neither lobe can complete the whole task alone.

## Evaluation

Clinical benchmark and publication materials remain a study layer around the
runtime. Clinical hazard labels belong to evaluation, not to the runtime's
general reasoning protocol.

## Scope

Research software only. Not a clinical decision-support product and not for
patient care.
