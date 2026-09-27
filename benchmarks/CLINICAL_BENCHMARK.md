# Clinical benchmark

The primary benchmark is designed around **latent context-dependent hazards**:
the clinically relevant risk is present in the supplied patient context but is
not explicitly named in the user's question.

## Required design rules

- Every positive case must have a predetermined gold safety obligation.
- Positive cases should be paired with a matched/near-matched negative control.
- Gold labels are frozen before the primary experiment.
- A0, A1, A2, and A3 receive the same cases.
- Failed model calls stay in the denominator.
- No result may be manually replaced after inspection.
- The main dataset should be clinically reviewed before strong safety claims are made.

## Arms

- A0: single model
- A1: single model + self-review
- A2: independent dual-lobe, no external evidence
- A3: independent dual-lobe + frozen evidence retrieval

Run:

```bash
python evaluation/run_benchmark.py \
  --cases benchmarks/clinical_cases_v1.jsonl \
  --arms A0,A1,A2,A3 \
  --evidence evidence/evidence_manifest.json \
  --output results/raw_results.jsonl

python evaluation/metrics.py \
  --input results/raw_results.jsonl \
  --output results/metrics.json
```

The initial metric script reports hazard precision/recall and false-positive/
false-negative rates. It will be expanded before the primary study to include
failure-type recall, evidence-grounding accuracy, unnecessary blocking,
latency, token use, and confidence intervals.
