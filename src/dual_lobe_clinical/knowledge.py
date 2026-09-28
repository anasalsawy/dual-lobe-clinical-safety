"""Medical-knowledge retrieval for the supervisory lobe.

Retrieval is deterministic and done before B is called: the question and
every record fact are used as queries, and the top snippets are put into B's
prompt as numbered evidence [K1], [K2], ... B may cite only those IDs, and the
control gate rejects any other knowledge citation (control.ground_finding).
This keeps retrieval auditable and does not depend on a small local model's
tool-calling ability.

The corpus is the deploying institution's own: formulary monographs, drug
label excerpts, local guidelines. Format (JSON Lines):

    {"id": "label-simvastatin-4", "source": "Simvastatin US PI, sec. 4", "text": "..."}

No corpus is shipped. Without one, B relies on its own trained knowledge
and cites only patient facts; the receipt and result metadata say so.
"""

from __future__ import annotations

import json
import os
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

_STOP = {
    "the", "and", "for", "with", "mg", "daily", "dose", "patient", "of", "to", "in", "on", "at",
    "is", "a", "an", "or", "per", "day", "bid", "tid", "prn", "po", "iv",
}


def _tokens(text: str) -> set[str]:
    t = unicodedata.normalize("NFKC", text or "").casefold()
    return {w for w in re.findall(r"[a-z][a-z0-9-]+", t) if len(w) >= 3 and w not in _STOP}


@dataclass(frozen=True)
class Snippet:
    id: str
    source: str
    text: str


class KnowledgeSource(Protocol):
    def search(self, query: str, limit: int = 3) -> list[Snippet]: ...


class JsonlKnowledgeSource:
    def __init__(self, path: str | os.PathLike):
        self.path = Path(path)
        self.snippets: list[Snippet] = []
        self._tok: list[set[str]] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            snip = Snippet(str(row["id"]), str(row.get("source", "")), str(row["text"]))
            self.snippets.append(snip)
            self._tok.append(_tokens(snip.text + " " + snip.source))

    def search(self, query: str, limit: int = 3) -> list[Snippet]:
        q = _tokens(query)
        if not q:
            return []
        scored = [(len(q & t), i) for i, t in enumerate(self._tok)]
        scored = [(s, i) for s, i in scored if s >= 2]
        scored.sort(key=lambda x: (-x[0], x[1]))
        return [self.snippets[i] for _, i in scored[:limit]]


def from_env() -> KnowledgeSource | None:
    path = os.getenv("DUAL_LOBE_CLINICAL_KNOWLEDGE_PATH", "").strip()
    return JsonlKnowledgeSource(path) if path else None


def retrieve_for_view(source: KnowledgeSource | None, queries: list[str], *, per_query: int = 2, cap: int = 12) -> dict[str, Snippet]:
    """Retrieve evidence for a request. Returns {"K1": snippet, ...} in retrieval order."""
    if source is None:
        return {}
    chosen: dict[str, Snippet] = {}
    seen: set[str] = set()
    for q in queries:
        for snip in source.search(q, limit=per_query):
            if snip.id in seen:
                continue
            seen.add(snip.id)
            chosen[f"K{len(chosen) + 1}"] = snip
            if len(chosen) >= cap:
                return chosen
    return chosen


def render(evidence: dict[str, Snippet]) -> str:
    if not evidence:
        return "(no knowledge corpus configured; rely on established clinical knowledge and cite patient facts)"
    return "\n".join(f"[{k}] ({s.source}) {s.text}" for k, s in evidence.items())
