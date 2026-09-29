from __future__ import annotations

import asyncio
import hashlib
import json
import os
import threading
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse, urlunparse
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class NativeInferenceState:
    state_key: str
    base_url: str
    slot_id: int
    filename: str
    extra_body: dict


class NativeInferenceStateManager:
    """Best-effort provider-native inference-state continuity.

    This intentionally does NOT emulate continuity with summaries or replay.
    It only activates when the backend exposes native KV/prompt-cache state.

    llama.cpp is supported through:
      - a stable id_slot per lobe/state_key
      - cache_prompt=true on inference requests
      - /slots/{id}?action=save|restore when slot persistence is enabled

    Unsupported providers are left untouched.
    """

    def __init__(self) -> None:
        self.enabled = os.getenv("DUAL_LOBE_NATIVE_STATE", "true").lower() in {
            "1", "true", "yes", "on"
        }
        self.timeout_s = float(os.getenv("DUAL_LOBE_NATIVE_STATE_TIMEOUT_SECONDS", "1.5"))
        self._lock = threading.RLock()
        self._support: dict[str, list[int] | None] = {}
        self._assignments: dict[tuple[str, str], int] = {}
        self._checkpointed: set[tuple[str, str]] = set()
        self._slot_locks: dict[tuple[str, int], threading.Lock] = {}

    @staticmethod
    def _server_root(base_url: str | None) -> str | None:
        if not base_url:
            return None
        try:
            p = urlparse(base_url)
        except Exception:
            return None
        if p.scheme not in {"http", "https"} or not p.netloc:
            return None
        path = p.path.rstrip("/")
        if path.endswith("/v1"):
            path = path[:-3]
        return urlunparse((p.scheme, p.netloc, path.rstrip("/"), "", "", ""))

    def _request_json(self, method: str, url: str, payload: dict | None = None):
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        req = Request(
            url,
            data=data,
            method=method,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "dual-lobe-native-state/1.0",
            },
        )
        with urlopen(req, timeout=self.timeout_s) as response:
            body = response.read(1_000_000).decode("utf-8", errors="ignore")
        return json.loads(body) if body.strip() else None

    def _probe_slots_sync(self, root: str) -> list[int] | None:
        with self._lock:
            if root in self._support:
                return self._support[root]

        try:
            payload = self._request_json("GET", f"{root}/slots")
            if not isinstance(payload, list):
                slots = None
            else:
                found: list[int] = []
                for row in payload:
                    if not isinstance(row, dict):
                        continue
                    value = row.get("id")
                    if value is None:
                        value = row.get("id_slot")
                    try:
                        found.append(int(value))
                    except Exception:
                        continue
                slots = sorted(set(found)) or None
        except Exception:
            slots = None

        with self._lock:
            self._support[root] = slots
        return slots

    async def _probe_slots(self, root: str) -> list[int] | None:
        return await asyncio.to_thread(self._probe_slots_sync, root)

    def _choose_slot(self, root: str, state_key: str, slots: list[int]) -> int | None:
        key = (root, state_key)
        with self._lock:
            if key in self._assignments:
                return self._assignments[key]

            explicit_name = "DUAL_LOBE_STATE_SLOT_" + "".join(
                c if c.isalnum() else "_" for c in state_key.upper()
            )
            raw = os.getenv(explicit_name, "").strip()
            if raw:
                try:
                    requested = int(raw)
                    if requested in slots:
                        self._assignments[key] = requested
                        return requested
                except ValueError:
                    pass

            used = {
                slot
                for (assigned_root, _), slot in self._assignments.items()
                if assigned_root == root
            }
            free = [slot for slot in slots if slot not in used]
            if not free:
                return None
            chosen = free[0]
            self._assignments[key] = chosen
            return chosen

    @staticmethod
    def _filename(state_key: str) -> str:
        digest = hashlib.sha256(state_key.encode("utf-8")).hexdigest()[:20]
        return f"dual_lobe_state_{digest}.bin"

    async def prepare(self, *, base_url: str | None, state_key: str | None) -> NativeInferenceState | None:
        if not self.enabled or not state_key:
            return None
        root = self._server_root(base_url)
        if not root:
            return None
        slots = await self._probe_slots(root)
        if not slots:
            return None
        slot_id = self._choose_slot(root, state_key, slots)
        if slot_id is None:
            return None

        state = NativeInferenceState(
            state_key=state_key,
            base_url=root,
            slot_id=slot_id,
            filename=self._filename(state_key),
            extra_body={"id_slot": slot_id, "cache_prompt": True},
        )

        lock_key = (root, slot_id)
        with self._lock:
            slot_lock = self._slot_locks.setdefault(lock_key, threading.Lock())
        await asyncio.to_thread(slot_lock.acquire)

        # Restore only when we have previously saved this state in this process.
        # On a fresh process, attempt restore once as well; missing-file errors are harmless.
        checkpoint_key = (root, state_key)
        try:
            await asyncio.to_thread(
                self._request_json,
                "POST",
                f"{root}/slots/{slot_id}?action=restore",
                {"filename": state.filename},
            )
        except Exception:
            pass
        return state

    async def checkpoint(self, state: NativeInferenceState | None) -> None:
        if state is None:
            return
        try:
            await asyncio.to_thread(
                self._request_json,
                "POST",
                f"{state.base_url}/slots/{state.slot_id}?action=save",
                {"filename": state.filename},
            )
            with self._lock:
                self._checkpointed.add((state.base_url, state.state_key))
        except Exception:
            # cache_prompt/id_slot still preserves in-process KV reuse even if
            # persistent slot save is not enabled on the server.
            pass
        finally:
            self.release(state)

    def release(self, state: NativeInferenceState | None) -> None:
        if state is None:
            return
        key = (state.base_url, state.slot_id)
        with self._lock:
            lock = self._slot_locks.get(key)
        if lock and lock.locked():
            try:
                lock.release()
            except RuntimeError:
                pass


class ContinuitySnapshotStore:
    """Role-scoped working-state snapshots for seamless behavioral continuation.

    This is used for every persistent model role, including hosted providers that
    cannot expose native KV state. It keeps only that role's own prior request/
    response stream and feeds it back on the next call. When native KV/slot state
    is available, both mechanisms can operate together.
    """

    def __init__(self) -> None:
        self.enabled = os.getenv("DUAL_LOBE_CONTINUITY_SNAPSHOTS", "true").lower() in {
            "1", "true", "yes", "on"
        }
        self.path = os.getenv(
            "DUAL_LOBE_CONTINUITY_PATH",
            ".dual_lobe_continuity_snapshots.json",
        )
        self._lock = threading.RLock()
        self._state: dict[str, list[dict[str, str]]] = {}
        self._loaded = False

    def _load_once(self) -> None:
        with self._lock:
            if self._loaded:
                return
            self._loaded = True
            try:
                with open(self.path, "r", encoding="utf-8") as fh:
                    raw = json.load(fh)
                if isinstance(raw, dict):
                    for key, rows in raw.items():
                        if isinstance(key, str) and isinstance(rows, list):
                            clean = []
                            for row in rows:
                                if not isinstance(row, dict):
                                    continue
                                request = row.get("request")
                                response = row.get("response")
                                if isinstance(request, str) and isinstance(response, str):
                                    clean.append({"request": request, "response": response})
                            self._state[key] = clean
            except Exception:
                pass

    def _persist(self) -> None:
        try:
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(self._state, fh, ensure_ascii=False)
            os.replace(tmp, self.path)
        except Exception:
            pass

    def context(self, state_key: str | None) -> str:
        if not self.enabled or not state_key:
            return ""
        self._load_once()
        with self._lock:
            rows = list(self._state.get(state_key, []))
        if not rows:
            return ""
        parts = [
            "CONTINUITY SNAPSHOT — continue as the same ongoing working thread. "
            "This is your own immediately preceding working context, not a new task summary."
        ]
        for row in rows:
            parts.append("PRIOR REQUEST:\n" + row["request"])
            parts.append("PRIOR RESPONSE:\n" + row["response"])
        return "\n\n".join(parts)

    def checkpoint(self, state_key: str | None, request: str, response: str) -> None:
        if not self.enabled or not state_key:
            return
        self._load_once()
        with self._lock:
            self._state.setdefault(state_key, []).append(
                {"request": request, "response": response}
            )
            self._persist()

    def clear(self, state_key: str | None = None) -> None:
        self._load_once()
        with self._lock:
            if state_key is None:
                self._state.clear()
            else:
                self._state.pop(state_key, None)
            self._persist()


CONTINUITY_SNAPSHOTS = ContinuitySnapshotStore()

NATIVE_INFERENCE_STATE = NativeInferenceStateManager()
