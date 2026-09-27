from __future__ import annotations

import argparse
import json
import secrets
from pathlib import Path

from dual_lobe_clinical.benchmark_validation import load_jsonl
from dual_lobe_clinical.gold_review import export_gold_review_cases


def main() -> None:
    p=argparse.ArgumentParser()
    p.add_argument("--cases",default="benchmarks/clinical_cases_v2.jsonl")
    p.add_argument("--review-output",default="results/gold_review/gold_review_packet.jsonl")
    p.add_argument("--key-output",default="results/gold_review/gold_review_key.json")
    p.add_argument("--salt",default="")
    args=p.parse_args()

    cases=load_jsonl(args.cases)
    salt=args.salt or secrets.token_hex(32)
    packet,key=export_gold_review_cases(cases,salt=salt)

    review_path=Path(args.review_output)
    key_path=Path(args.key_output)
    review_path.parent.mkdir(parents=True,exist_ok=True)
    key_path.parent.mkdir(parents=True,exist_ok=True)

    review_path.write_text(
        "".join(json.dumps(x,ensure_ascii=False)+"\n" for x in packet),
        encoding="utf-8",
    )
    key_path.write_text(
        json.dumps({
            "salt":salt,
            "mapping":key,
            "warning":"Keep mapping separate if reviewers should be blinded to internal case IDs."
        },indent=2),
        encoding="utf-8",
    )
    print(f"wrote {len(packet)} case-review records")


if __name__=="__main__":
    main()
