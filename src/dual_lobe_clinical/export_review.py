from __future__ import annotations

import argparse
import json
import secrets
from pathlib import Path

from dual_lobe_clinical.adjudication import (
    export_blinded_review_package,
    write_jsonl,
)


def load_jsonl(path: str) -> list[dict]:
    return [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--input", default="results/raw_results.jsonl")
    p.add_argument("--review-output", default="results/review/blinded_review.jsonl")
    p.add_argument("--key-output", default="results/review/blinding_key.json")
    p.add_argument("--salt", default="")
    args = p.parse_args()

    rows = load_jsonl(args.input)
    salt = args.salt or secrets.token_hex(32)
    package, key = export_blinded_review_package(rows, salt=salt)

    review_path = Path(args.review_output)
    key_path = Path(args.key_output)
    review_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.parent.mkdir(parents=True, exist_ok=True)

    write_jsonl(review_path, package)
    key_path.write_text(
        json.dumps({
            "blinding_salt": salt,
            "mapping": key,
            "warning": "Keep this file inaccessible to blinded reviewers until adjudication is locked."
        }, indent=2),
        encoding="utf-8",
    )
    print(f"wrote {len(package)} blinded samples to {review_path}")
    print(f"wrote arm/case mapping to {key_path}")


if __name__ == "__main__":
    main()
