from __future__ import annotations

import argparse
import json
from dual_lobe_clinical.freeze import build_primary_freeze


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--cases", default="benchmarks/clinical_cases_v2.jsonl")
    p.add_argument("--guardian-manifest", default="guardian/guardian_manifest.json")
    p.add_argument("--gold-reviews", required=True)
    p.add_argument("--gold-review-key", required=True)
    p.add_argument("--output-dir", required=True)
    args = p.parse_args()

    manifest = build_primary_freeze(
        cases_path=args.cases,
        guardian_manifest_path=args.guardian_manifest,
        gold_reviews_path=args.gold_reviews,
        gold_review_key_path=args.gold_review_key,
        output_dir=args.output_dir,
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
