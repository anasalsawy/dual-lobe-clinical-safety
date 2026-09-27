from __future__ import annotations

import json
import re
from dataclasses import asdict
from pathlib import Path
from typing import Iterable

from .schemas import EvidenceRecord


_WORD = re.compile(r"[a-z0-9]+")


class FrozenEvidenceStore:
    """Versionable evidence registry used for reproducible experiments.

    The primary-study store is frozen: no live web browsing occurs during a
    benchmark run. Retrieval is deterministic lexical matching over versioned
    records so the same query/case can be reproduced exactly.
    """

    def __init__(self, records: Iterable[EvidenceRecord] = ()) -> None:
        self._records = {r.evidence_id: r for r in records}

    def add(self, record: EvidenceRecord) -> None:
        if record.evidence_id in self._records:
            raise ValueError(f"duplicate evidence id: {record.evidence_id}")
        self._records[record.evidence_id] = record

    def get(self, evidence_id: str) -> EvidenceRecord | None:
        return self._records.get(evidence_id)

    def records(self) -> tuple[EvidenceRecord, ...]:
        return tuple(self._records.values())

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

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return {m.group(0) for m in _WORD.finditer((text or "").lower()) if len(m.group(0)) > 2}

    def retrieve(self, text: str, *, limit: int = 12) -> tuple[EvidenceRecord, ...]:
        """Deterministic lexical retrieval for frozen-study evidence.

        Score = weighted token overlap with tags/title/excerpt/source.
        Stable ID ordering breaks ties, avoiding run-to-run drift.
        """
        query = self._tokens(text)
        if not query or not self._records:
            return ()
        scored: list[tuple[int, str, EvidenceRecord]] = []
        for record in self._records.values():
            tag_tokens = self._tokens(" ".join(record.tags))
            title_tokens = self._tokens(record.title)
            excerpt_tokens = self._tokens(record.excerpt)
            source_tokens = self._tokens(record.source)
            score = (
                5 * len(query & tag_tokens)
                + 3 * len(query & title_tokens)
                + 2 * len(query & excerpt_tokens)
                + len(query & source_tokens)
            )
            if score > 0:
                scored.append((score, record.evidence_id, record))
        scored.sort(key=lambda x: (-x[0], x[1]))
        return tuple(item[2] for item in scored[: max(1, limit)])

    @staticmethod
    def render(records: Iterable[EvidenceRecord], *, max_chars: int = 24000) -> str:
        rows: list[str] = []
        used = 0
        for r in records:
            row = (
                f"EVIDENCE_ID: {r.evidence_id}\n"
                f"SOURCE: {r.source}\nTITLE: {r.title}\n"
                f"VERSION_OR_DATE: {r.version_or_date}\n"
                f"SOURCE_ORG: {r.source_org}\nSOURCE_TYPE: {r.source_type}\n"
                f"SOURCE_URL: {r.source_url}\nSOURCE_LOCATOR: {r.source_locator}\n"
                f"TAGS: {', '.join(r.tags)}\nEVIDENCE_PROPOSITION: {r.excerpt}"
            )
            if used + len(row) > max_chars:
                break
            rows.append(row)
            used += len(row)
        return "\n\n".join(rows) if rows else "(no matching frozen evidence records)"

    @classmethod
    def load_json(cls, path: str | Path) -> "FrozenEvidenceStore":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        records = []
        for item in raw.get("records", []):
            normalized = dict(item)
            normalized["tags"] = tuple(normalized.get("tags") or ())
            records.append(EvidenceRecord(**normalized))
        return cls(records)

    def dump_json(self, path: str | Path) -> None:
        payload = {"records": [asdict(r) for r in self._records.values()]}
        Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
