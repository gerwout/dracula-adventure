"""Disk-backed snapshot store for resumable web sessions.

One JSON file per opaque session token: {"state": <serialize(eng)>, "lang": <code>,
"ts": <epoch seconds>, "active": <{"key":..., "slot":...} | None>}. `active` is the
named-save identity (derived HMAC key + slot only -- never the raw name/PIN) so a cold
resume can restore it and per-turn autosave re-engages; old records simply have no
`active` key, and `.get("active")` returns None for them. Writes are atomic (tmp +
os.replace). `reap` enforces the TTL and a hard file-count cap. Token filenames are
sanitised so a hostile token can never escape the directory. All operations tolerate
missing/corrupt files (return None / skip)."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

_SAFE = re.compile(r"[^A-Za-z0-9_-]")


def _safe_name(token: str) -> str | None:
    # tokens are secrets.token_urlsafe -> [A-Za-z0-9_-]; reject anything else outright
    if not token or _SAFE.search(token):
        return None
    return token + ".json"


class SessionStore:
    def __init__(self, directory, max_files: int = 50_000, cap_check_every: int = 256) -> None:
        self.dir = Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)
        # Amortized write-time cap: the hourly reaper enforces the count cap, but a burst of
        # new sessions between sweeps could exhaust disk/inodes — so every _cap_check_every
        # writes we cheaply prune down to _max_files (oldest first). Keeps the cost off the
        # hot path while bounding the directory to ~max_files + cap_check_every.
        self._max_files = max_files
        self._cap_check_every = max(1, cap_check_every)
        self._writes_since_cap = 0

    def _path(self, token: str) -> Path | None:
        name = _safe_name(token)
        return (self.dir / name) if name else None

    @staticmethod
    def _read_record(path: Path) -> dict | None:
        # Tolerates missing/corrupt files and JSON that parses but isn't a
        # dict (e.g. "[]", "null", a bare string/number) -> None either way.
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
        return data if isinstance(data, dict) else None

    def save(self, token: str, state: dict, lang: str, active: dict | None = None) -> None:
        p = self._path(token)
        if p is None:
            return
        import time
        rec = {"state": state, "lang": lang, "ts": time.time(), "active": active}
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(rec), encoding="utf-8")
        os.replace(tmp, p)
        self._writes_since_cap += 1
        if self._writes_since_cap >= self._cap_check_every:
            self._writes_since_cap = 0
            self._enforce_count_cap()

    def _enforce_count_cap(self) -> None:
        """Prune the directory down to _max_files (oldest by mtime first). Cheap: uses
        stat, not JSON reads. Missing/racing files are skipped. Called amortized from save."""
        entries = []
        for p in self.dir.glob("*.json"):
            try:
                entries.append((p.stat().st_mtime, p))
            except OSError:
                continue
        excess = len(entries) - self._max_files
        if excess <= 0:
            return
        entries.sort()                       # oldest mtime first
        for _mtime, p in entries[:excess]:
            try:
                p.unlink()
            except OSError:
                pass

    def load(self, token: str) -> dict | None:
        p = self._path(token)
        if p is None or not p.exists():
            return None
        return self._read_record(p)

    def exists(self, token: str) -> bool:
        p = self._path(token)
        return bool(p and p.exists())

    def reap(self, ttl: float, max_files: int, now: float) -> int:
        files = []
        for p in self.dir.glob("*.json"):
            rec = self._read_record(p) or {}
            ts = rec.get("ts", 0)
            ts = ts if isinstance(ts, (int, float)) else 0
            files.append((ts, p))
        deleted = 0
        keep = []
        for ts, p in files:
            if now - ts > ttl:
                try:
                    p.unlink(); deleted += 1
                except OSError:
                    pass
            else:
                keep.append((ts, p))
        if len(keep) > max_files:
            keep.sort()  # oldest ts first
            for ts, p in keep[: len(keep) - max_files]:
                try:
                    p.unlink(); deleted += 1
                except OSError:
                    pass
        return deleted
