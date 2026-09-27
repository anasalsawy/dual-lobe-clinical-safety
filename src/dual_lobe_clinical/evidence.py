from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Iterable

from .schemas import EvidenceRecord


class FrozenEvidenceStore:
    """Versionable evidence registry used for reproducible experiments.

    The store does not browse the live web. Benchmark runs should point to a
    frozen JSON corpus so the same evidence is available to every study arm.
    """

    def __init__(self, records: Iterable[EvidenceRecord] = ()) -> None:
        self._records = {r.evidence_id: r for r in records}

    def add(self, record: EvidenceRecord) -> None:
        if record.evidence_id in self._records:
            raise ValueError(f"duplicate evidence id: {record.evidence_id}")
        self._records[record.evidence_id] = record

    def get(self, evidence_id: str) -> EvidenceRecord | None:
        return self._records.get(evidence_id)

    def contains_all(self, evidence_ids: Iterable[str]) -> bool:
        return all(eid in self._records for eid in evidence_ids)

    def search_tags(self, *tags: str) -> tuple[EvidenceRecord, ...]:
        wanted = {t.strip().lower() for t in tags if t.strip()}
        if not wanted:
            return ()
        matches = []
        for record in self._records.values():
            record_tags = {t.lower() for t in record.tags}
            if wanted & record_tags:
                matches.append(record)
        return tuple(matches)

    @classmethod
    def load_json(cls, path: str | Path) -> "FrozenEvidenceStore":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(EvidenceRecord(**item) for item in raw["records"])

    def dump_json(self, path: str | Path) -> None:
        payload = {"records": [asdict(r) for r in self._records.values()]}
        Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
