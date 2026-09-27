# Clinical benchmark

The benchmark is designed around latent context-dependent hazards: the clinically relevant risk is present in the supplied patient context but is not explicitly named in the user's question.

## Required design rules

- Every positive case has a predetermined gold safety obligation.
- Positive cases are paired with matched or near-matched negative controls.
- Gold labels are frozen before the primary experiment.
- Failed model calls stay in the denominator.
- No result may be manually replaced after inspection.
- The dataset should be clinically reviewed before strong safety claims are made.

Run:

    python evaluation/run_benchmark.py --cases benchmarks/clinical_cases_v2.jsonl --output results/raw_results.jsonl

The benchmark evaluates the implemented Dual-Lobe clinical system directly.
